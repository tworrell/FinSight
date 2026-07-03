from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

_EXPORT_MIME_MAP = {
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.document": "text/html",
}


def build_drive_service(creds: Credentials) -> Resource:
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_folders(service: Resource, query: str | None = None) -> list[dict]:
    q = "mimeType='application/vnd.google-apps.folder' and trashed=false"
    if query:
        safe = query.replace("'", "\\'")
        q += f" and name contains '{safe}'"
    results = (
        service.files()
        .list(q=q, fields="files(id, name)", pageSize=100, orderBy="name")
        .execute()
    )
    return results.get("files", [])


def list_files_in_folder(service: Resource, folder_id: str, modified_after: str | None = None) -> list[dict]:
    q = f"'{folder_id}' in parents and trashed=false"
    if modified_after:
        q += f" and modifiedTime > '{modified_after}'"
    results = (
        service.files()
        .list(q=q, fields="files(id, name, mimeType, modifiedTime)", pageSize=200, orderBy="modifiedTime")
        .execute()
    )
    return results.get("files", [])


def download_file(service: Resource, file_id: str, mime_type: str) -> bytes:
    if mime_type in _EXPORT_MIME_MAP:
        return service.files().export(fileId=file_id, mimeType=_EXPORT_MIME_MAP[mime_type]).execute()
    return service.files().get_media(fileId=file_id).execute()
