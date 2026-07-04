import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_oauth_redirect_uri],
        }
    }


# google-auth-oauthlib defaults to PKCE (autogenerate_code_verifier=True): the Flow instance
# that builds the authorization URL generates a code_verifier, and the *same* verifier must be
# presented when exchanging the code for a token. Since the auth-url step and the callback are
# handled by separate requests (and therefore separate Flow objects), we stash the verifier
# from the first step here and hand it to the second. Fine for this single-tenant demo — a
# multi-user version would key this by the `state` param instead of just holding the latest one.
_pending_code_verifier: str | None = None


def build_flow(code_verifier: str | None = None) -> Flow:
    return Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=settings.google_oauth_redirect_uri,
        code_verifier=code_verifier,
    )


def get_auth_url() -> str:
    global _pending_code_verifier
    flow = build_flow()
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # ensures we get a refresh_token even on repeat connects
    )
    _pending_code_verifier = flow.code_verifier
    return auth_url


def exchange_code(code: str) -> Credentials:
    flow = build_flow(code_verifier=_pending_code_verifier)
    flow.fetch_token(code=code)
    creds = flow.credentials
    _save_credentials(creds)
    return creds


def _save_credentials(creds: Credentials) -> None:
    settings.token_store_path.parent.mkdir(parents=True, exist_ok=True)
    settings.token_store_path.write_text(creds.to_json())


def load_credentials() -> Credentials | None:
    if not settings.token_store_path.exists():
        return None
    data = json.loads(settings.token_store_path.read_text())
    creds = Credentials.from_authorized_user_info(data, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)
    return creds


def is_connected() -> bool:
    return load_credentials() is not None
