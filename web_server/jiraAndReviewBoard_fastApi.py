from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# JIRA Configuration
jira_url = "https://ipo-jira.rbbn.com/jira"
jira_api_token = os.getenv("JIRA_API_TOKEN")
jira_headers = {
    "Authorization": f"Bearer {jira_api_token}",
    "Content-Type": "application/json"
}

# Review Board Configuration
REVIEWBOARD_DOMAIN = "http://revbrd01.ecitele.com/reviews"
reviewboard_api_token = os.getenv("REVIEW_BOARD_API_TOKEN")
reviewboard_headers = {
    "Authorization": f"token {reviewboard_api_token}",
    "Accept": "application/json"
}

# Filter JIRA issue data
def filtered_jira_json(issue):
    fields = issue.get('fields', {})
    return {
        "Issue Key": issue.get('key'),
        "Summary": fields.get('summary'),
        "issuetype": fields.get('issuetype', {}).get('name') if fields.get('issuetype') else None,
        "status": fields.get('status', {}).get('name') if fields.get('status') else None,
        "creator": fields.get('creator', {}).get('displayName') if fields.get('creator') else None,
        "Severity": fields['customfield_10423']['value'] if fields.get('customfield_10423') and isinstance(fields.get('customfield_10423'), dict) else None,
        "reporter": fields.get('reporter', {}).get('displayName') if fields.get('reporter') else None,
        "Stopper": fields['customfield_10007']['value'] if fields.get('customfield_10007') and isinstance(fields.get('customfield_10007'), dict) else None,
        "fixVersions": fields['fixVersions'][0]['name'] if fields.get('fixVersions') and len(fields['fixVersions']) > 0 and isinstance(fields['fixVersions'][0], dict) else None,
        "priority": fields.get('priority', {}).get('name') if fields.get('priority') else None,
        "duedate": fields.get('duedate')
    }


@app.get("/jira/issues")
def get_jira_issues():
    jql_query = "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"
    encoded_jql = requests.utils.quote(jql_query)
    URL = f"{jira_url}/rest/api/2/search?jql={encoded_jql}"

    response = requests.get(URL, headers=jira_headers)
    if response.status_code == 200:
        issues = response.json().get('issues', [])
        filtered_data = [filtered_jira_json(issue) for issue in issues if issue['fields']['issuetype']['name'] == "PR"]
        return JSONResponse(content=filtered_data)
    else:
        return JSONResponse(status_code=response.status_code, content={"error": response.text})

# Extract tags from Review Board description
def extract_tags(description):
    if "Jira:" in description and "Fix Description:" in description:
        jira_match = re.search(r'Jira:\s*(\S+)', description)
        fix_match = re.search(r'Fix Description:\s*(.*?)(?:Impacts UI|$)', description, re.DOTALL)

        jira_id = jira_match.group(1).strip() if jira_match else None
        fix_description = fix_match.group(1).strip() if fix_match else None

        return jira_id, fix_description
    else:
        return None

@app.get("/reviewboard/requests")
def get_review_requests():
    session_url = f"{REVIEWBOARD_DOMAIN}/api/session/"
    response = requests.get(session_url, headers=reviewboard_headers)

    if response.status_code != 200:
        return JSONResponse(status_code=response.status_code, content={"error": "Failed to fetch Review Board user info"})

    username = response.json()['session']['links']['user']['title']
    reviewboard_api_url = f"{REVIEWBOARD_DOMAIN}/api/review-requests/?to-users={username}"

    try:
        response = requests.get(reviewboard_api_url, headers=reviewboard_headers)
        response.raise_for_status()
        data = response.json()

        review_requests = data.get('review_requests', [])
        all_requests = []

        for request in review_requests:
            request_data = {}
            jira_id = None

            request_data['id'] = request['id']
            result = extract_tags(request['description'])
            if result:
                jira_id, fix_description = result
                request_data['description'] = fix_description
            else:
                request_data['description'] = request['description']

            reviewers = request['target_people']
            reviewer_list = [r['title'] for r in reviewers]
            request_data['submitter'] = request['links']['submitter']['title']
            request_data['reviewers'] = reviewer_list
            request_data['labels'] = []
            request_data['due_date'] = ''

            if jira_id:
                issue_url = f"{jira_url}/rest/api/2/issue/{jira_id}"
                response = requests.get(issue_url, headers=jira_headers)
                if response.status_code == 200:
                    issue = response.json()
                    request_data['labels'] = issue['fields'].get('labels', [])
                    request_data['due_date'] = issue['fields'].get('duedate', '')

            all_requests.append(request_data)

        return JSONResponse(content=all_requests)

    except requests.exceptions.RequestException as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
