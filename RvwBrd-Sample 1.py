import requests
import json
import re
from dotenv import load_dotenv
import os

load_dotenv()

jira_url = "https://ipo-jira.rbbn.com/jira"
jira_api_token = os.getenv("JIRA_API_TOKEN")
# jira_api_token = "<JIRA-api-token>"

jira_headers = {
    "Authorization": f"Bearer {jira_api_token}",
    "Content-Type": "application/json"
}

REVIEWBOARD_DOMAIN = "http://revbrd01.ecitele.com/reviews"
API_TOKEN = os.getenv("REVIEW_BOARD_API_TOKEN")
# API_TOKEN = "<Review-Board-Token>"


# Headers for authentication and response format
headers = {
    "Authorization": f"token {API_TOKEN}",
    "Accept": "application/json"
}

session_url = f"{REVIEWBOARD_DOMAIN}/api/session/"
response = requests.get(session_url, headers=headers)

username =""
if response.status_code == 200:
    user_data = response.json()
    username = user_data['session']['links']['user']['title']
else:
    print(f"Failed to fetch user info: {response.status_code} - {response.text}")


REVIEWBOARD_API_URL = f"{REVIEWBOARD_DOMAIN}/api/review-requests/?to-users={username}"
#REVIEWBOARD_API_URL = "http://revbrd01.ecitele.com/reviews/api/users/"



def extract_tags(description):
    if "Jira:" in description and "Fix Description:" in description:
        jira_match = re.search(r'Jira:\s*(\S+)', description)
        fix_match = re.search(r'Fix Description:\s*(.*?)(?:Impacts UI|$)', description, re.DOTALL)

        jira_id = jira_match.group(1).strip() if jira_match else None
        fix_description = fix_match.group(1).strip() if fix_match else None

        return jira_id, fix_description

    else:
        return None


def get_review_requests():
    all_requests = []

    try:
        response = requests.get(REVIEWBOARD_API_URL, headers=headers)
        response.raise_for_status()
        data = response.json()

        review_requests = data.get('review_requests', [])
        if not review_requests:
            print("No review requests found.")
        else:
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

                # Default values
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

        # Save all collected data to a JSON file
        with open('review_requests.json', 'w') as f:
            json.dump(all_requests, f, indent=4)

        print("Review request data saved to review_requests.json")

    except requests.exceptions.RequestException as e:
        print(f"Error accessing Review Board API: {e}")

if __name__ == "__main__":
    get_review_requests()