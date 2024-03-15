import os
import json
import tkinter as tk
from tkinter import filedialog
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import schedule
import time

# File to store the selected path and Google Drive credentials
CONFIG_FILE = "config.json"
SCOPES = ['https://www.googleapis.com/auth/drive']


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        return None


# Function to save configuration to file
def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)


# Function to select directory for DICOM files
def select_directory():
    selected_dir = filedialog.askdirectory()
    if selected_dir:
        config = {"dicom_directory": selected_dir}
        save_config(config)
        return selected_dir
    else:
        return None


# Function to authenticate with Google Drive API
def authenticate_google_drive():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

# Function to upload file to Google Drive if it doesn't already exist
def upload_to_drive(service, file_path, folder_id):
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    try:
        # Check if the file already exists in Google Drive
        results = service.files().list(
            q=f"name='{file_metadata['name']}' and parents in '{folder_id}'",
            fields='files(id)'
        ).execute()
        files = results.get('files', [])
        if files:
            print(f"File '{file_metadata['name']}' already exists in Google Drive. Skipping upload.")
            return

        # File doesn't exist, upload it
        file = service.files().create(body=file_metadata,
                                      media_body=media,
                                      fields='id').execute()
        print('File ID: %s' % file.get('id'))
    except Exception as e:
        print(f"An error occurred while uploading {file_path}: {e}")



# Function to get DICOM files from selected directory
def get_dicom_files(directory):
    dicom_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.dcm'):
                dicom_files.append(os.path.join(root, file))
    return dicom_files


# Function to perform synchronization
def sync():
    # Load configuration
    config = load_config()
    if config and "dicom_directory" in config:
        dicom_directory = config["dicom_directory"]
    else:
        dicom_directory = select_directory()
        if not dicom_directory:
            print("No directory selected. Exiting.")
            return

    # Authenticate with Google Drive API
    creds = authenticate_google_drive()
    if not creds:
        print("Failed to authenticate with Google Drive API. Exiting.")
        return
    drive_service = build('drive', 'v3', credentials=creds)

    # Get DICOM files from selected directory
    dicom_files = get_dicom_files(dicom_directory)

    # Specify the folder ID where you want to save the DICOM files
    folder_id = '1HXO9Tk2ej8lrpc0HzwjTOHHhji1_gxPo'

    # Upload DICOM files to Google Drive
    for file in dicom_files:
        upload_to_drive(drive_service, file, folder_id)


# Main function
def main():
    # Run the synchronization immediately
    sync()

    # Schedule synchronization every 1 hour
    schedule.every(1).hours.do(sync)

    # Keep the script running to execute scheduled tasks
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
