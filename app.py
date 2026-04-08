import os
import json
import logging
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

CALENDAR_ID = 'chbilal.2332@gmail.com'
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds_raw = os.environ.get('GOOGLE_CREDENTIALS', '')
    creds_dict = json.loads(creds_raw)
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('calendar', 'v3', credentials=creds)

@app.route('/')
def home():
    return jsonify({"status": "ok"})

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        data = payload.get('args', payload)
        app.logger.info(f"DATA: {data}")

        name = str(data.get('name', 'Guest'))
        date_str = str(data.get('date', ''))
        time_str = str(data.get('time', ''))
        party_size = data.get('party_size', 1)
        phone = str(data.get('phone', ''))

        dt_str = f"{date_str} {time_str}"
        formats = ['%Y-%m-%d %I:%M %p', '%Y-%m-%d %H:%M', '%Y-%m-%d %I:%M%p']
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_str.strip(), fmt)
                break
            except ValueError:
                continue

        if dt is None:
            return jsonify({"success": False, "message": f"Could not parse: {dt_str}"}), 400

        tz = pytz.timezone('America/Chicago')
        dt_start = tz.localize(dt)
        dt_end = dt_start + timedelta(hours=1)

        event = {
            'summary': f'Reservation - {name} (Party of {party_size})',
            'description': f'Name: {name}\nParty size: {party_size}\nPhone: {phone}',
            'start': {'dateTime': dt_start.isoformat(), 'timeZone': 'America/Chicago'},
            'end': {'dateTime': dt_end.isoformat(), 'timeZone': 'America/Chicago'},
        }

        service = get_calendar_service()
        created = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        return jsonify({"success": True, "message": f"Booking confirmed for {name} on {date_str} at {time_str} for {party_size} guests."})

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/check_availability', methods=['POST'])
def check_availability():
    return jsonify({"available": True, "message": "We have availability. What date works for you?"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
