from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json, os

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = 'chbilal.2332@gmail.com'  # e.g. your Gmail address

def get_calendar_service():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=creds)


@app.route('/check_availability', methods=['POST'])
def check_availability():
    data = request.json
    date_str = data.get('date')        # e.g. "2026-04-10"
    time_str = data.get('time')        # e.g. "14:00"
    
    try:
        service = get_calendar_service()
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(hours=1)

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_dt.isoformat() + '-05:00',
            timeMax=end_dt.isoformat() + '-05:00',
            singleEvents=True
        ).execute()

        events = events_result.get('items', [])
        if events:
            return jsonify({"available": False, "message": f"That time slot is already booked. Please suggest a different time."})
        else:
            return jsonify({"available": True, "message": f"{date_str} at {time_str} is available."})
    except Exception as e:
        return jsonify({"available": False, "message": "Could not check availability right now."}), 500


@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    data = request.json
    caller_name = data.get('caller_name', 'Unknown')
    phone       = data.get('phone_number', '')
    date_str    = data.get('date')           # "2026-04-10"
    time_str    = data.get('time')           # "14:00"
    note        = data.get('note', '')

    try:
        service = get_calendar_service()
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt   = start_dt + timedelta(hours=1)

        event = {
            'summary': f'Appointment — {caller_name}',
            'description': f'Phone: {phone}\nNote: {note}\nBooked via AI Receptionist',
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/Chicago'},
            'end':   {'dateTime': end_dt.isoformat(),   'timeZone': 'America/Chicago'},
        }

        created = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return jsonify({
            "success": True,
            "message": f"Got it! I've booked {caller_name} for {date_str} at {time_str}. You'll receive a confirmation shortly."
        })
    except Exception as e:
        return jsonify({"success": False, "message": "I wasn't able to complete the booking. The agent will follow up to confirm."}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "running"})


if __name__ == '__main__':
    app.run(debug=True)
