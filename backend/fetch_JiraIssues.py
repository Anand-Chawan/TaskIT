import requests
import json
import sys
from dotenv import load_dotenv
import os

load_dotenv()
api_token = os.getenv("JIRA_API_TOKEN")


def filteredJson(issue):
    filtered_item = {}
    filtered_item["Issue Key"] = issue['key']
    filtered_item["Summary"] = issue['fields']['summary']
    filtered_item["issuetype"] = issue['fields']['issuetype']['name']
    filtered_item["status"] = issue['fields']['status']['name']
    filtered_item["creator"] = issue['fields']['creator']['displayName']
    filtered_item["Severity"] = issue['fields']['customfield_10423']['value']
    filtered_item["reporter"] = issue['fields']['reporter']['displayName']
    filtered_item["Stopper"] = issue['fields']['customfield_10007']['value']
    filtered_item["fixVersions"] = issue['fields']['fixVersions'][0]['name']
    filtered_item["priority"] = issue['fields']['priority']['name']
    filtered_item["duedate"] = issue['fields']['duedate']
    return filtered_item

def printJson(issue):
    print(f"Issue Key: {issue['key']}")
    print(f"Summary: {issue['fields']['summary']}")
    print(f"issuetype: {issue['fields']['issuetype']['name']}")
    print(f"status: {issue['fields']['status']['name']}")
    print(f"creator: {issue['fields']['creator']['displayName']}")
    print(f"Severity: {issue['fields']['customfield_10423']['value']}")
    print(f"reporter: {issue['fields']['reporter']['displayName']}")
    print(f"Stopper: {issue['fields']['customfield_10007']['value']}")
    print(f"fixVersions: {issue['fields']['fixVersions'][0]['name']}")
    print(f"priority: {issue['fields']['priority']['name']}")
    print(f"duedate: {issue['fields']['duedate']}")

###################################
# Redirect output to a log file
f = open('log.txt', 'w')
sys.stdout = f
sys.stderr = f

######################################
jira_url = "https://ipo-jira.rbbn.com/jira"

headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

jql_query = "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"
encoded_jql = requests.utils.quote(jql_query)

###################################################################
URL = f"{jira_url}/rest/api/2/search?jql={encoded_jql}"
response = requests.get(URL, headers=headers)

if response.status_code == 200:
    issues = response.json()
    issues = issues['issues']
    # print(json.dumps(issues, indent=4))
    filtered_data = []
    for issue in issues:
        # print(issue)
        if issue['fields']['issuetype']['name'] == "PR":
            filtered_data.append(filteredJson(issue))
            # print("\n\n\n")
else:
    print(f"Error: {response.status_code}")
    print(response.text)

# Save all collected data to a JSON file
with open('jira_issues.json', 'w') as f:
    json.dump(filtered_data, f, indent=4)
print(filtered_data)