from flask import Flask, request, jsonify
import os
import json
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

def get_calendar_service():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise Exception("GOOGLE_CREDENTIALS environment variable not set")
    
    creds_data = json.loads(creds_json)
    
    creds = Credentials(
        token=creds_data.get("token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data.get("client_id"),
        client_secret=creds_data.get("client_secret"),
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    
    service = build("calendar", "v3", credentials=creds)
    return service

@app.route("/")
def health():
    return jsonify({"status": "ok"})

@app.route("/book_appointment", methods=["POST"])
def book_appointment():
    try:
        data = request.json
        calendar_id = data.get("calendar_id", "primary")
        date = data.get("date")
        time = data.get("time")
        duration = data.get("duration", 60)
        caller_name = data.get("caller_name", "Patient")
        caller_phone = data.get("caller_phone", "")
        notes = data.get("notes", "")

        start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=int(duration))

        event = {
            "summary": f"Appointment - {caller_name}",
            "description": f"Phone: {caller_phone}\nNotes: {notes}",
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "America/Chicago"
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "America/Chicago"
            }
        }

        service = get_calendar_service()
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        return jsonify({
            "success": True,
            "event_id": created_event["id"],
            "event_link": created_event.get("htmlLink", ""),
            "message": f"Appointment booked for {caller_name} on {date} at {time}"
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
