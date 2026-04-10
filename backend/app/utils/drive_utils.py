import base64
import io
import json
import os

from fastapi import UploadFile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

def load_drive_service():
    encoded_creds = os.getenv("GOOGLE_CREDENTIALS_BASE64")  # ✅ This must match Railway
    if not encoded_creds:
        raise ValueError("Missing GOOGLE_CREDENTIALS_BASE64 in environment")

    creds_dict = json.loads(base64.b64decode(encoded_creds).decode())
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    print("[Drive] ✅ Google Drive service loaded successfully.")
    return build("drive", "v3", credentials=credentials)



def upload_to_drive(file: UploadFile,folder_id: str) -> str:
    print(f"[Upload] 📁 Attempting upload to folder ID: {folder_id}")
    print(f"[Upload] 📄 File name: {file.filename}, Content type: {file.content_type}")
    drive_service=load_drive_service()
    media_body=MediaIoBaseUpload(file.file,mimetype=file.content_type)
    #Prepare metadata
    file_metadata={
        "name":file.filename,
        "parents":[folder_id]
    }
    print(f"[Upload] Metadata being sent: {file_metadata}")
    try:
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media_body,
            fields="id, name, parents"
        ).execute()
        print(f"[Upload] ✅ File uploaded successfully with ID: {uploaded_file['id']}")
        print(f"[Upload] 📂 File parents: {uploaded_file.get('parents')}")
        return uploaded_file["id"]
    except Exception as e:
        print(f"[Upload] ❌ Upload failed: {e}")
        raise


    return uploaded_file["id"]