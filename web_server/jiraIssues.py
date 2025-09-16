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
def filteredJson(issue):
    return {
        "Issue Key": issue['key'],
        "Summary": issue['fields']['summary'],
        "issuetype": issue['fields']['issuetype']['name'],
        "status": issue['fields']['status']['name'],
        "creator": issue['fields']['creator']['displayName'],
        "Severity": issue['fields']['customfield_10423']['value'],
        "reporter": issue['fields']['reporter']['displayName'],
        "Stopper": issue['fields']['customfield_10007']['value'],
        "fixVersions": issue['fields']['fixVersions'][0]['name'] if issue['fields']['fixVersions'] else None,
        "priority": issue['fields']['priority']['name']
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
