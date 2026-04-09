import os
import json
import time
import logging
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# In-memory cache — one entry per sheet_id
_cache = {}
CACHE_TTL = 60  # seconds

def get_credentials():
    creds_raw = os.environ.get('GOOGLE_CREDENTIALS', '')
    creds_dict = json.loads(creds_raw)
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

def get_sheets_data(sheet_id):
    now = time.time()
    if sheet_id in _cache and (now - _cache[sheet_id]["timestamp"]) < CACHE_TTL:
        return _cache[sheet_id]["data"]

    sheets = build('sheets', 'v4', credentials=get_credentials())
    result = sheets.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range='Sheet1!A:B'
    ).execute()

    rows = result.get('values', [])
    info = {}
    for row in rows[1:]:
        if len(row) >= 2:
            info[row[0].strip().lower()] = row[1].strip()

    _cache[sheet_id] = {"data": info, "timestamp": now}
    return info

@app.route('/')
def home():
    return jsonify({"status": "ok"})

@app.route('/lookup_info', methods=['POST'])
def lookup_info():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        data = payload.get('args', payload)
        key = str(data.get('key', '')).strip().lower()
        sheet_id = str(data.get('sheet_id', '')).strip()

        if not sheet_id:
            return jsonify({"success": False, "message": "sheet_id is required"}), 400

        info = get_sheets_data(sheet_id)

        if key in info:
            return jsonify({"success": True, "value": info[key]})
        else:
            return jsonify({"success": True, "value": info})

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
