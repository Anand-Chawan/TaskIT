from fastapi.middleware.cors import CORSMiddleware 
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
import google.generativeai as genai



load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
GEMINI_API=os.getenv("GOOGLE_API_KEY")

# Helper Functions
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
@app.get("/api/jira/")
def get_jira_issues():
    jql_query = "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"
    encoded_jql = requests.utils.quote(jql_query)
    URL = f"{jira_url}/rest/api/2/search?jql={encoded_jql}"
    response = requests.get(URL, headers=jira_headers)
    if response.status_code == 200:
        issues = response.json().get('issues', [])
        filtered_data = [filtered_jira_json(issue) for issue in issues]        
        with open("jira.json", "w") as f:
            json.dump(filtered_data, f, indent=2)
        return JSONResponse(content=filtered_data)
    else:
        return JSONResponse(status_code=response.status_code, content={"error": response.text})

@app.get("/api/review-board/")
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
        with open('review_requests.json', 'w') as f:
            json.dump(all_requests, f, indent=4)
        return JSONResponse(content=all_requests)
    except requests.exceptions.RequestException as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/meetings/")
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
    with open("calendar_events.json", "w") as f:
        json.dump(formatted_today, f, indent=2)
    return JSONResponse(content=formatted_today)

@app.get("/api/taskscheduler/")
def get_gemini_taskscheduler():
    genai.configure(api_key=GEMINI_API)

    # Choose the model
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Load JSON files
    with open("calendar_events.json", "r") as f:
        calendar = json.load(f)

    with open("review_requests.json", "r") as f:
        reviews = json.load(f)

    with open("jira.json", "r") as f:
        jira_tasks = f.readlines()

    # Build prompt
    prompt = f"""
    Generate a daily task schedule for me based on the provided JSON data.

    **Working Hours and Duration Estimates:**
    *   My working hours are strictly from 9:00 AM to 5:00 PM.
    *   Jira tasks take approximately 3 hours each.
    *   Review tasks take approximately 30 minutes each.
    *   Assume a 1-hour lunch break must be scheduled if there's a contiguous block of at least 2 hours available between 11:30 AM and 2:00 PM.

    **Exclusion and Truncation Rules for Calendar Events:**
    *   Exclude calendar events marked as 'Canceled'.
    *   Exclude calendar events that are completely outside working hours (9 AM - 5 PM).
    *   For calendar events partially outside working hours, truncate their `start_time` to 9:00 AM if it's before, and their `end_time` to 5:00 PM if it's after.

    **Scheduling Logic - Step-by-Step:**

    1.  **Initialize Daily Schedule:** Start with a clean schedule for 9:00 AM to 5:00 PM.
    2.  **Integrate Meetings First:**
        *   Add all valid (non-canceled, within/truncated to working hours) `Meeting` events to the schedule. Meetings are fixed and cannot be moved or split.
        *   Meetings take absolute precedence and create immutable blocks of busy time.
    3.  **Identify Available Time Slots:** After placing all meetings, determine the contiguous blocks of free time throughout the day.
    4.  **Prioritize Non-Meeting Tasks:**
        *   Create a single prioritized list of all `Jira` and `Review` tasks based on these rules, in descending order of importance:
            a.  `Review` tasks by `due_date` (earliest date first). If `due_date` is the same, use the `id` for stable ordering (ascending).
            b.  `Jira` tasks by `Severity` (Critical > Major > Minor > null/undefined).
            c.  `Jira` tasks by `Stopper` ('MKT Stopper' first, then 'Not Defined'/'No Stopper'/'null').
            d.  `Jira` tasks by `priority` (High > Medium > Low > 'Not Prioritized'/null).
            e.  For tasks with identical priority by all above rules, use the `task_id` for `Jira` tasks (alphanumeric ascending) and `id` for `Review` tasks (numeric ascending) for stable ordering.
    5.  **Schedule Non-Meeting Tasks into Available Slots:**
        *   Iterate through the prioritized non-meeting tasks.
        *   For each task, attempt to fit it into the *earliest available time slot* that can accommodate its full duration.
        *   **Task Splitting:** If a task's duration is longer than any single available time slot, it *must be split* into multiple parts to fit into available slots. Each split part should be represented as a separate entry in the output schedule, with its own `start_time` and `end_time` and the same task details (summary, task_id, etc.). Append "(Part X)" to the summary for split tasks (e.g., "[EMB] IO-App Implementation (Part 1)").
        *   **Lunch Break Insertion:** Before scheduling any non-meeting tasks, check if a 1-hour lunch break is needed and can be inserted. Find the largest available contiguous block of time between 11:30 AM and 2:00 PM that is at least 2 hours long. If found, schedule a 1-hour `Break` type task named "Lunch Break" within that block, centered if possible. Once scheduled, this break also creates an immutable block.
        *   Continue scheduling tasks until all tasks are scheduled or no more time slots are available.
    6.  **Ensure Logical Time Progression:** All `start_time` must be before `end_time` for every scheduled item. No overlaps are permitted in the final schedule.

    **Output Format Requirements:**
    The output MUST be a JSON array of objects, where each object represents a scheduled item (Meeting, Jira, Review, or Break). The response MUST contain ONLY the JSON array, with no additional text or markdown formatting (like ```json).

    Each object must include:
    -   `start_time`: (String, HH:MM AM/PM format, e.g., "09:00 AM")
    -   `end_time`: (String, HH:MM AM/PM format, e.g., "09:30 PM")
    -   `task_type`: (String, "Meeting", "Jira", "Review", or "Break")
    -   `summary`: (String, the subject for meetings, summary for Jira, description for reviews, or "Lunch Break" for breaks)

    Additionally, based on `task_type`:

    *   For `task_type: "Jira"`:
        -   `task_id`: (String, `Issue Key`)
        -   `severity`: (String, `Severity`, can be null)
        -   `stopper`: (String, `Stopper`, can be null)

    *   For `task_type: "Review"`:
        -   `task_id`: (Integer, `id`)
        -   `due_date`: (String, `due_date`)

    *   For `task_type: "Meeting"`:
        -   `organizer`: (String, `organizer`)

    *   For `task_type: "Break"`:
        -   `task_id`: (null)

    **Input JSON Files:**

    ### calendar_events.json ###
    {json.dumps(calendar, indent=2)}

    ### jira.json ###
    {json.dumps(jira_tasks, indent=2)}

    ### review_requests.json ###
    {json.dumps(reviews, indent=2)}
    """

    # Send a prompt
    response = model.generate_content(prompt)

    valid_response = response.text
    cleaned_text = valid_response[8:-4]

    # Parse the cleaned text into JSON
    try:
        parsed_json = json.loads(cleaned_text)
        with open('AI_Task_Scheduler.json', 'w') as f:
            json.dump(parsed_json, f, indent=4)
        return JSONResponse(content=parsed_json)

    except requests.exceptions.RequestException as e:
        return JSONResponse(status_code=500, content={"error": str(e)})