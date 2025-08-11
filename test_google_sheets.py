"""
Sanitized Google Sheets Test Script (no hard-coded credentials)
Reads credentials path from environment variable GOOGLE_CREDENTIALS instead of storing it in code.
"""

import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def test_google_sheets():
    credentials_file = os.getenv('GOOGLE_CREDENTIALS')
    if not credentials_file or not os.path.exists(credentials_file):
        print("Google credentials file not found. Set GOOGLE_CREDENTIALS environment variable.")
        return
    
    try:
        # Use credentials to create a client to interact with the Google Drive API
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)

        # Find a workbook by name
        sheet = client.open("AlgoTradingSystem")

        # Print all worksheet names
        print("Available worksheets:", sheet.worksheets())

        # Access the Trade_Log worksheet
        trade_log = sheet.worksheet("Trade_Log")
        print("Trade_Log worksheet found!")

        # Add a test row
        trade_log.append_row(["Test", "Data", "Verification"])
        print("Test data added successfully!")
    
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")

if __name__ == "__main__":
    test_google_sheets()
