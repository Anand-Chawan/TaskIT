
import msal
import requests
from datetime import datetime, timezone, timedelta
import os
import json
from tzlocal import get_localzone
from zoneinfo import ZoneInfo

# === Replace with your Azure app credentials ===
CLIENT_ID = "client-id"
TENANT_ID = "tenant-id"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

GRAPH_ENDPOINT = 'https://graph.microsoft.com/v1.0/me/calendar/events'

SCOPES = ['Calendars.Read']

# === Token cache file ===
CACHE_FILE = "token_cache.json"

# Load or create token cache
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

app = msal.PublicClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    token_cache=token_cache
)

accounts = app.get_accounts()
if accounts:
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
else:
    result = None

if not result:
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)

save_cache()

def Fetch_data(events, isToday):
    if events:
        for event in events:
            #print(event)
            subject = event.get("subject", "No Subject")
            start = event.get("start", {}).get("dateTime", "N/A")
            end = event.get("end", {}).get("dateTime", "N/A")
            location = event.get("location", {}).get("displayName", "No Location")
            organizer = event.get("organizer", {}).get("emailAddress", {}).get("name", "No Name")
            attendance_type=""

            for attendee in event.get("attendees", []):
                email = attendee.get("emailAddress", {}).get("address", "")
                if email.lower() == my_email.lower():
                    attendance_type = attendee.get("type", "unknown")
                    break

            # Format times
            try:
                start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc).astimezone(local_tz)
                end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc).astimezone(local_tz)
                start_str = start_dt.strftime("%I:%M %p")
                end_str = end_dt.strftime("%I:%M %p")
                date_str = start_dt.strftime("%Y-%m-%d")
            except Exception:
                start_str = start
                end_str = end

            print(f"{subject}")
            print(f"{start_str} - {end_str}")
            if not isToday:
                print(f"{date_str}")
            print(f"{location}")
            print(f"{organizer}")
            print(f"{attendance_type}\n")
    else:
        print("✅ No calendar events found for today.")

if "access_token" in result:
    token = result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get user's profile info
    profile_response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    profile_data = profile_response.json()

    # Extract and print email
    my_email = profile_data.get("mail") 

    local_tz = get_localzone()

    # Get today's date range
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, datetime.min.time()).isoformat() + "Z"
    end_of_day = datetime.combine(today, datetime.max.time()).isoformat() + "Z"

    print(f"\n📅 Today's Calendar Events ({today}):\n")
    url = f"https://graph.microsoft.com/v1.0/me/calendar/calendarView?startDateTime={start_of_day}&endDateTime={end_of_day}"
    response = requests.get(url, headers=headers)
    events = response.json().get("value", [])
    Fetch_data(events,True)
    
    past_24_hours = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"

    # Microsoft Graph filter query
    print(f"\nMeetings Scheduled in past 24 hours:\n")
    url = f"https://graph.microsoft.com/v1.0/me/events?$filter=createdDateTime ge {past_24_hours}"
    response = requests.get(url, headers=headers)
    events = response.json().get("value", [])
    Fetch_data(events,False)

else:
    print("❌ Failed to acquire token:", result.get("error_description"))
