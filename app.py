import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_credentials():
    creds_raw = os.environ.get('GOOGLE_CREDENTIALS', '')
    creds_dict = json.loads(creds_raw)
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

def get_calendar_service():
    return build('calendar', 'v3', credentials=get_credentials())

@app.route('/')
def home():
    return jsonify({"status": "ok"})

@app.route('/check_availability', methods=['POST'])
def check_availability():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        data = payload.get('args', payload)

        calendar_id = str(data.get('calendar_id', '')).strip()
        date = str(data.get('date', '')).strip()

        if not calendar_id or not date:
            return jsonify({"success": False, "message": "calendar_id and date are required"}), 400

        service = get_calendar_service()

        start = f"{date}T00:00:00Z"
        end = f"{date}T23:59:59Z"

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        booked_times = []
        for event in events:
            start_time = event['start'].get('dateTime', event['start'].get('date'))
            end_time = event['end'].get('dateTime', event['end'].get('date'))
            booked_times.append({"start": start_time, "end": end_time})

        return jsonify({
            "success": True,
            "date": date,
            "booked_slots": booked_times,
            "total_booked": len(booked_times)
        })

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        data = payload.get('args', payload)

        calendar_id = str(data.get('calendar_id', '')).strip()
        date = str(data.get('date', '')).strip()
        time = str(data.get('time', '')).strip()
        duration = int(data.get('duration', 60))
        caller_name = str(data.get('caller_name', 'Unknown'))
        caller_phone = str(data.get('caller_phone', ''))
        notes = str(data.get('notes', ''))

        if not calendar_id or not date or not time:
            return jsonify({"success": False, "message": "calendar_id, date, and time are required"}), 400

        service = get_calendar_service()

        start_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration)

        event = {
            'summary': f"Appointment - {caller_name}",
            'description': f"Phone: {caller_phone}\nNotes: {notes}",
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Chicago',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Chicago',
            },
        }

        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        return jsonify({
            "success": True,
            "message": f"Appointment booked for {caller_name} on {date} at {time}",
            "event_id": created_event.get('id'),
            "event_link": created_event.get('htmlLink')
        })

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
