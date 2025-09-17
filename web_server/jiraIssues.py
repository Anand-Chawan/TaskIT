from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
api_token = os.getenv("JIRA_API_TOKEN")

app = FastAPI()

# Function to filter JIRA issue data
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
    jira_url = "https://ipo-jira.rbbn.com/jira"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    jql_query = "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"
    encoded_jql = requests.utils.quote(jql_query)
    URL = f"{jira_url}/rest/api/2/search?jql={encoded_jql}"

    response = requests.get(URL, headers=headers)

    if response.status_code == 200:
        issues = response.json().get('issues', [])
        filtered_data = [
            filteredJson(issue)
            for issue in issues
            if issue['fields']['issuetype']['name'] == "PR"
        ]
        return JSONResponse(content=filtered_data)
    else:
        return JSONResponse(status_code=response.status_code, content={"error": response.text})
