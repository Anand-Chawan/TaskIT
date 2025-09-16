
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
import os
import re
from dotenv import load_dotenv
import json
from datetime import datetime, timezone, timedelta
from tzlocal import get_localzone
import msal

load_dotenv()
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

# Microsoft Teams Configuration
CLIENT_ID = os.getenv("TEAMS_CLIENT_ID")
TENANT_ID = os.getenv("TEAMS_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ['Calendars.Read']
CACHE_FILE = "token_cache.json"

# Helper Functions
def filtered_jira_json(issue):
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

def extract_tags(description):
    if "Jira:" in description and "Fix Description:" in description:
        jira_match = re.search(r'Jira:\s*(\S+)', description)
        fix_match = re.search(r'Fix Description:\s*(.*?)(?:Impacts UI|$)', description, re.DOTALL)
        jira_id = jira_match.group(1).strip() if jira_match else None
        fix_description = fix_match.group(1).strip() if fix_match else None
        return jira_id, fix_description
    else:
        return None

# Endpoints
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

@app.get("/teams/calendar")
def get_teams_calendar():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache_data = json.load(f)
            token_cache = msal.SerializableTokenCache()
            token_cache.deserialize(json.dumps(cache_data))
    else:
        token_cache = msal.SerializableTokenCache()

    def save_cache():
        if token_cache.has_state_changed:
            with open(CACHE_FILE, "w") as f:
                f.write(token_cache.serialize())

    app_msal = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=token_cache)
    accounts = app_msal.get_accounts()
    if accounts:
        result = app_msal.acquire_token_silent(SCOPES, account=accounts[0])
    else:
        result = app_msal.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in result:
            return JSONResponse(status_code=500, content={"error": "Failed to initiate device flow"})
        print(result["message"])
        result = app_msal.acquire_token_by_device_flow(result)

    save_cache()

    if "access_token" not in result:
        return JSONResponse(status_code=401, content={"error": result.get("error_description", "Token acquisition failed")})

    token = result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    profile_data = profile_response.json()
    my_email = profile_data.get("mail")
    local_tz = get_localzone()

    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, datetime.min.time()).isoformat() + "Z"
    end_of_day = datetime.combine(today, datetime.max.time()).isoformat() + "Z"

    url_today = f"https://graph.microsoft.com/v1.0/me/calendar/calendarView?startDateTime={start_of_day}&endDateTime={end_of_day}"
    response_today = requests.get(url_today, headers=headers)
    events_today = response_today.json().get("value", [])

    past_24_hours = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
    url_recent = f"https://graph.microsoft.com/v1.0/me/events?$filter=createdDateTime ge {past_24_hours}"
    response_recent = requests.get(url_recent, headers=headers)
    events_recent = response_recent.json().get("value", [])

    def format_event(event, isToday):
        subject = event.get("subject", "No Subject")
        start = event.get("start", {}).get("dateTime", "N/A")
        end = event.get("end", {}).get("dateTime", "N/A")
        location = event.get("location", {}).get("displayName", "No Location")
        organizer = event.get("organizer", {}).get("emailAddress", {}).get("name", "No Name")
        attendance_type = ""
        Attendees_list=[]                
        for attendee in event.get("attendees", []):
            Attendees_list.append(attendee.get("emailAddress", {}).get("name", ""))
            email = attendee.get("emailAddress", {}).get("address", "")
            if email.lower() == my_email.lower():
                attendance_type = attendee.get("type", "unknown")
        try:
            start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc).astimezone(local_tz)
            end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc).astimezone(local_tz)
            start_str = start_dt.strftime("%I:%M %p")
            end_str = end_dt.strftime("%I:%M %p")
            date_str = start_dt.strftime("%Y-%m-%d")
        except Exception:
            start_str = start
            end_str = end
            date_str = ""
        return {
            "subject": subject,
            "start": start_str,
            "end": end_str,
            "date": date_str if not isToday else "Today",
            "location": location,
            "organizer": organizer,
            "attendance_type": attendance_type,
            "Attendees_list": Attendees_list
        }

    formatted_today = [format_event(e, True) for e in events_today]
    formatted_recent = [format_event(e, False) for e in events_recent]

    return JSONResponse(content={"today_events": formatted_today, "recent_events": formatted_recent})
