import json
import re
from io import BytesIO

from google.oauth2 import service_account
import googleapiclient.discovery
from googleapiclient.http import MediaIoBaseDownload

from db import connect_db

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_ACCOUNT_FILE = "google-auth.json"


def get_doc_id(url):
    fmt = re.compile(r"/d/(.*)/")
    doc_id = fmt.search(url).group(1)
    return doc_id


def get_credentials():
    with connect_db() as db:
        data = json.loads(db("SELECT data FROM auth_json").fetchone()[0])
    return service_account.Credentials.from_service_account_info(
        data, scopes=SCOPES
    )


def load_document(*, url=None, doc_id=None):
    doc_id = doc_id or get_doc_id(url)

    service = googleapiclient.discovery.build(
        "drive", "v3", credentials=get_credentials()
    )
    request = service.files().export_media(fileId=doc_id, mimeType="text/plain")

    file = BytesIO()
    downloader = MediaIoBaseDownload(file, request)

    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print(status, "Download {:d}%.".format(int(status.progress() * 100)))

    return file.getvalue().decode("utf-8")


def load_sheet(*, url=None, doc_id=None, sheet_name):
    service = googleapiclient.discovery.build(
        "sheets", "v4", credentials=get_credentials()
    )
    doc_id = doc_id or get_doc_id(url)
    result = service.spreadsheets().values().get(spreadsheetId=doc_id, range=sheet_name).execute()
    return result["values"]
