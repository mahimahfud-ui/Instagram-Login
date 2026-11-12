import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, abort, redirect, render_template_string, request, session, url_for
from sqlalchemy import DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("ig-insights")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(days=14),
    MAX_CONTENT_LENGTH=1024 * 1024,
)

INSTAGRAM_CLIENT_ID = os.getenv("INSTAGRAM_APP_ID", "").strip()
INSTAGRAM_CLIENT_SECRET = os.getenv("INSTAGRAM_APP_SECRET", "").strip()
INSTAGRAM_REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI", "").strip()
INSTAGRAM_SCOPES = [
    scope.strip()
    for scope in os.getenv("INSTAGRAM_SCOPES", "instagram_business_basic").split(",")
    if scope.strip()
]
AUTHORIZE_URL = "https://www.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"
GRAPH_BASE = "https://graph.instagram.com"
HTTP_TIMEOUT = (5, 20)


def _database_url():
    value = os.getenv("DATABASE_URL", "sqlite:///./instagram_oauth_local.sqlite3").strip()
    if value.startswith("postgres://"):
        value = "postgresql+psycopg://" + value[len("postgres://"):]
    elif value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


database_url = _database_url()
engine_options = {"pool_pre_ping": True}
if database_url.startswith("sqlite:"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(database_url, **engine_options)
DBSession = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class InstagramConnection(Base):
    __tablename__ = "instagram_connections"

    session_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    instagram_user_id: Mapped[str] = mapped_column(String(80), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(40), nullable=False, default="Professional")
    profile_picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_count: Mapped[int | None] = mapped_column(nullable=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Base.metadata.create_all(engine)


def token_cipher():
    seed = (app.config["SECRET_KEY"] + "|instagram-token-storage-v1").encode("utf-8")
    derived = hashlib.sha256(seed).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def is_configured():
    if not (INSTAGRAM_CLIENT_ID and INSTAGRAM_CLIENT_SECRET and INSTAGRAM_REDIRECT_URI):
        return False
    parsed = urlparse(INSTAGRAM_REDIRECT_URI)
    return parsed.scheme == "https" and bool(parsed.netloc)


def safe_https_url(value):
    if not value:
        return None
    parsed = urlparse(str(value))
    return str(value) if parsed.scheme == "https" and parsed.netloc else None


def current_session_id():
    session_id = session.get("app_session_id")
    if not session_id:
        session_id = secrets.token_urlsafe(32)
        session["app_session_id"] = session_id
    return session_id


def get_connection():
    session_id = session.get("app_session_id")
    if not session_id:
        return None
    with DBSession() as db:
        row = db.get(InstagramConnection, session_id)
        if not row:
            return None
        try:
            token = token_cipher().decrypt(row.encrypted_access_token.encode()).decode()
        except (InvalidToken, ValueError):
            logger.error("Stored Instagram token could not be decrypted; forcing reconnect.")
            return None
        return {
            "session_id": row.session_id,
            "instagram_user_id": row.instagram_user_id,
            "username": row.username,
            "account_type": row.account_type,
            "profile_picture_url": safe_https_url(row.profile_picture_url),
            "media_count": row.media_count,
            "access_token": token,
            "token_expires_at": row.token_expires_at,
        }


def save_connection(session_id, profile, access_token, expires_in):
    now = datetime.now(timezone.utc)
    row_data = {
        "session_id": session_id,
        "instagram_user_id": str(profile["id"]),
        "username": str(profile.get("username") or "Instagram account"),
        "account_type": str(profile.get("account_type") or "Professional"),
        "profile_picture_url": safe_https_url(profile.get("profile_picture_url")),
        "media_count": profile.get("media_count"),
        "encrypted_access_token": token_cipher().encrypt(access_token.encode()).decode(),
        "token_expires_at": now + timedelta(seconds=max(int(expires_in), 3600)),
        "updated_at": now,
    }
    with DBSession.begin() as db:
        row = db.get(InstagramConnection, session_id)
        if row is None:
            db.add(InstagramConnection(**row_data))
        else:
            for key, value in row_data.items():
                setattr(row, key, value)


def delete_connection(session_id):
    with DBSession.begin() as db:
        row = db.get(InstagramConnection, session_id)
        if row is not None:
            db.delete(row)


def instagram_get(path, access_token, extra_params=None):
    params = {"access_token": access_token}
    if extra_params:
        params.update(extra_params)
    response = requests.get(
        f"{GRAPH_BASE}/{path.lstrip('/')}",
        params=params,
        timeout=HTTP_TIMEOUT,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if not response.ok or "error" in payload:
        api_error = payload.get("error", {}) if isinstance(payload, dict) else {}
        code = api_error.get("code", response.status_code) if isinstance(api_error, dict) else response.status_code
        raise RuntimeError(f"Instagram API request failed (code {code}).")
    return payload


def refresh_token_if_needed(connection):
    expires_at = connection["token_expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at - datetime.now(timezone.utc) > timedelta(days=7):
        return connection
    refreshed = instagram_get(
        "/refresh_access_token",
        connection["access_token"],
        {"grant_type": "ig_refresh_token"},
    )
    new_token = refreshed.get("access_token")
    if not new_token:
        raise RuntimeError("Instagram did not return a refreshed access token.")
    save_connection(
        connection["session_id"],
        {
            "id": connection["instagram_user_id"],
            "username": connection["username"],
            "account_type": connection["account_type"],
            "profile_picture_url": connection["profile_picture_url"],
            "media_count": connection["media_count"],
        },
        new_token,
        refreshed.get("expires_in", 5184000),
    )
    return get_connection()


def exchange_authorization_code(code):
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": INSTAGRAM_CLIENT_ID,
            "client_secret": INSTAGRAM_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": INSTAGRAM_REDIRECT_URI,
            "code": code,
        },
        timeout=HTTP_TIMEOUT,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if not response.ok or not payload.get("access_token"):
        error = payload.get("error_type") or payload.get("error") or "token_exchange_failed"
        raise RuntimeError(f"Instagram authorization could not be completed ({error}).")

    short_lived_token = payload["access_token"]
    long_response = requests.get(
        f"{GRAPH_BASE}/access_token",
        params={
            "grant_type": "ig_exchange",
            "client_secret": INSTAGRAM_CLIENT_SECRET,
            "access_token": short_lived_token,
        },
        timeout=HTTP_TIMEOUT,
    )
    try:
        long_payload = long_response.json()
    except ValueError:
        long_payload = {}
    if not long_response.ok or not long_payload.get("access_token"):
        raise RuntimeError("Instagram did not issue a long-lived access token.")
    return long_payload["access_token"], long_payload.get("expires_in", 5184000)


def render_message(title, message, status=400):
    return render_template_string(MESSAGE_TEMPLATE, title=title, message=message), status


HOME_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>IG Insights · Connect</title><style>
:root{color-scheme:light;--ink:#172033;--muted:#697386;--line:#e8eaf0;--accent:#6d48dc}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:radial-gradient(circle at 15% 10%,#f3eaff,transparent 32%),#f7f8fc;color:var(--ink);font:15px Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:grid;place-items:center;padding:24px}
.card{width:min(100%,430px);background:#fff;border:1px solid var(--line);border-radius:24px;padding:34px;box-shadow:0 20px 70px #1c254012}
.brand{display:flex;align-items:center;gap:11px;font-weight:800;font-size:19px;letter-spacing:-.4px}.mark{width:40px;height:40px;border-radius:14px;background:linear-gradient(135deg,#ffb04a,#ed3986 55%,#7955e8);display:grid;place-items:center;color:white;font-size:20px}
h1{font-size:30px;line-height:1.1;letter-spacing:-1.1px;margin:35px 0 12px}.muted{color:var(--muted);line-height:1.65}
.connect{display:flex;justify-content:center;align-items:center;width:100%;padding:15px 18px;margin:26px 0 14px;border-radius:12px;text-decoration:none;color:white;background:linear-gradient(100deg,#e83d83,#7652df);font-weight:750;box-shadow:0 8px 22px #b14eab33}
.notice{padding:13px 14px;border:1px solid #e8eaf0;border-radius:12px;background:#fafbfe;color:#515b6c;font-size:13px;line-height:1.6}
.setup{margin-top:18px;color:#8b5061;font-size:13px;line-height:1.6}
footer{margin-top:24px;color:#98a0ae;font-size:11px;text-align:center}
</style></head><body><main class="card">
<div class="brand"><div class="mark">◎</div><span>IG Insights</span></div>
<h1>Connect your Instagram</h1>
<p class="muted">Securely connect an Instagram professional account to view the profile details and media data that Meta makes available to this app.</p>
{% if configured %}
<a class="connect" href="{{ url_for('instagram_auth_start') }}">Continue with Instagram</a>
{% else %}
<div class="notice">Instagram sign-in is not configured yet. The service owner must add the Instagram Business Login app credentials and the exact HTTPS callback URL in the hosting environment.</div>
{% endif %}
<div class="notice">You will be redirected to <strong>instagram.com</strong> to sign in and approve access. This app never asks for or receives your Instagram password.</div>
{% if not configured %}<p class="setup">Required server settings: INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET, INSTAGRAM_REDIRECT_URI and FLASK_SECRET_KEY.</p>{% endif %}
<footer>Independent application · Not affiliated with or endorsed by Instagram or Meta</footer>
</main></body></html>"""


MESSAGE_TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ title }}</title><style>
*{box-sizing:border-box}body{margin:0;background:#f7f8fc;font:15px Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172033;min-height:100vh;display:grid;place-items:center;padding:24px}.card{max-width:480px;width:100%;background:white;border:1px solid #e8eaf0;border-radius:20px;padding:30px;box-shadow:0 20px 70px #1c254012}h1{font-size:25px;margin:0 0 12px}p{color:#697386;line-height:1.65}a{color:#6d48dc;font-weight:700;text-decoration:none}
</style></head><body><main class="card"><h1>{{ title }}</h1><p>{{ message }}</p><a href="{{ url_for('index') }}">Back to start</a></main></body></html>"""


DASHBOARD_TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>IG Insights · Dashboard</title><style>
:root{--ink:#172033;--muted:#697386;--line:#e8eaf0;--surface:#fff;--accent:#7551d7}
*{box-sizing:border-box}body{margin:0;background:#f6f7fb;color:var(--ink);font:14px Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{height:72px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 max(22px,calc((100vw - 1120px)/2))}
.brand{font-weight:850;font-size:18px;letter-spacing:-.4px}.brand span{background:linear-gradient(90deg,#ed4e8c,#7955dc);background-clip:text;color:transparent}
main{width:min(1120px,calc(100% - 36px));margin:34px auto}
.eyebrow{font-size:11px;letter-spacing:1.4px;text-transform:uppercase;color:#939aaa;font-weight:800}
h1{font-size:29px;letter-spacing:-1px;margin:8px 0 6px}.sub{color:var(--muted);margin:0 0 24px}
.profile{display:flex;align-items:center;gap:15px;background:white;border:1px solid var(--line);border-radius:18px;padding:19px;margin-bottom:18px}
.avatar{width:62px;height:62px;border-radius:50%;object-fit:cover;background:#f0ebff}
.avatar-fallback{width:62px;height:62px;border-radius:50%;display:grid;place-items:center;background:#f0ebff;color:#7652df;font-size:25px;font-weight:800}
.handle{font-size:18px;font-weight:800}.type{font-size:12px;color:var(--muted);margin-top:5px}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:25px}
.stat,.media{background:white;border:1px solid var(--line);border-radius:17px;padding:18px}.stat .label{color:var(--muted);font-size:12px}.stat .value{font-size:27px;font-weight:850;letter-spacing:-.8px;margin-top:8px}
.section-head{display:flex;align-items:end;justify-content:space-between;margin:30px 0 14px}.section-head h2{font-size:19px;margin:0}.section-head span{color:var(--muted);font-size:12px}
.media-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.media{padding:0;overflow:hidden}.thumb{width:100%;aspect-ratio:1;object-fit:cover;background:#eee}.media-info{padding:13px}.kind{font-size:10px;font-weight:800;color:#7551d7;text-transform:uppercase}.caption{font-size:12px;line-height:1.5;margin:8px 0;color:#4d5668;overflow-wrap:anywhere}.media a{color:#7551d7;font-size:12px;font-weight:800;text-decoration:none}
.empty{background:white;border:1px dashed #d8dbe5;border-radius:16px;padding:24px;color:var(--muted);line-height:1.6}
.warning,.limits{border-radius:12px;padding:13px 15px;margin:15px 0;font-size:12px;line-height:1.6}.warning{background:#fff5ef;color:#92542d}.limits{background:#f0f1ff;color:#55517b}
.logout{border:1px solid var(--line);border-radius:10px;background:#fff;padding:10px 14px;color:#3d4658;font-weight:700;cursor:pointer}
@media(max-width:700px){header{padding:0 18px}main{margin:22px auto}.grid{grid-template-columns:1fr 1fr}.media-grid{grid-template-columns:1fr 1fr}h1{font-size:25px}}
@media(max-width:420px){.media-grid{grid-template-columns:1fr}.grid{gap:9px}.stat{padding:14px}.stat .value{font-size:23px}}
</style></head><body>
<header><div class="brand">IG <span>Insights</span></div>
<form method="post" action="{{ url_for('disconnect') }}"><input type="hidden" name="csrf_token" value="{{ csrf_token }}"><button class="logout" type="submit">Disconnect</button></form></header>
<main><div class="eyebrow">Connected account</div><h1>Account overview</h1><p class="sub">Live information returned by Instagram's official API.</p>
<section class="profile">
{% if profile_picture_url %}<img class="avatar" src="{{ profile_picture_url }}" alt="Instagram profile picture">{% else %}<div class="avatar-fallback">@</div>{% endif %}
<div><div class="handle">@{{ username }}</div><div class="type">{{ account_type }} account · Instagram account ID {{ instagram_user_id }}</div></div></section>
<section class="grid">
<div class="stat"><div class="label">Published media</div><div class="value">{{ media_count if media_count is not none else "—" }}</div></div>
<div class="stat"><div class="label">Recent media loaded</div><div class="value">{{ media|length }}</div></div>
<div class="stat"><div class="label">Connection</div><div class="value" style="font-size:19px">Active</div></div>
</section>
{% if media_warning %}<div class="warning">{{ media_warning }}</div>{% endif %}
<div class="section-head"><h2>Recent media</h2><span>Latest items provided by Instagram</span></div>
{% if media %}
<div class="media-grid">{% for item in media %}
<article class="media">
{% if item.image_url %}<img class="thumb" src="{{ item.image_url }}" alt="Instagram media" loading="lazy">{% else %}<div class="thumb" style="display:grid;place-items:center;color:#8a8fa0">Media preview unavailable</div>{% endif %}
<div class="media-info"><div class="kind">{{ item.media_type or "POST" }}</div>
{% if item.caption %}<p class="caption">{{ item.caption[:170] }}{% if item.caption|length > 170 %}…{% endif %}</p>{% endif %}
{% if item.permalink %}<a href="{{ item.permalink }}" target="_blank" rel="noopener noreferrer">Open on Instagram ↗</a>{% endif %}
</div></article>{% endfor %}</div>
{% else %}<div class="empty">Instagram did not return recent media for this account, or the account has no accessible posts.</div>{% endif %}
<div class="limits">API limitation: Instagram does not provide this app with a named list of profile visitors, people who blocked the account, or people who unfollowed the account. Those figures are not fabricated or displayed here.</div>
</main></body></html>"""


@app.get("/")
def index():
    if get_connection():
        return redirect(url_for("dashboard"))
    return render_template_string(HOME_TEMPLATE, configured=is_configured())


@app.get("/auth/instagram")
def instagram_auth_start():
    if not is_configured():
        return render_message(
            "Instagram connection is not configured",
            "The service owner must configure the Instagram Business Login app credentials and the exact HTTPS callback URL.",
            503,
        )
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    session.permanent = True
    current_session_id()
    params = {
        "client_id": INSTAGRAM_CLIENT_ID,
        "redirect_uri": INSTAGRAM_REDIRECT_URI,
        "response_type": "code",
        "scope": ",".join(INSTAGRAM_SCOPES),
        "state": state,
        "force_reauth": "true",
    }
    return redirect(f"{AUTHORIZE_URL}?{urlencode(params)}")


@app.get("/auth/instagram/callback")
def instagram_auth_callback():
    if request.args.get("error"):
        session.pop("oauth_state", None)
        return render_message(
            "Instagram authorization was not completed",
            "You cancelled the authorization or Instagram rejected the requested access. No password was collected by this app.",
            400,
        )
    expected_state = session.pop("oauth_state", None)
    received_state = request.args.get("state", "")
    if not expected_state or not received_state or not hmac.compare_digest(expected_state, received_state):
        return render_message("Security check failed", "The OAuth state did not match. Start the connection again.", 400)
    code = request.args.get("code", "")
    if not code or not is_configured():
        return render_message("Instagram did not return an authorization code", "Return to the start page and try again.", 400)

    try:
        access_token, expires_in = exchange_authorization_code(code)
        profile = instagram_get(
            "/me",
            access_token,
            {"fields": "id,username,account_type,media_count,profile_picture_url"},
        )
        if not profile.get("id"):
            raise RuntimeError("Instagram did not return the connected account ID.")
        save_connection(current_session_id(), profile, access_token, expires_in)
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        logger.warning("Instagram OAuth callback failed: %s", str(exc)[:180])
        return render_message(
            "Could not connect Instagram",
            "Meta did not complete the connection. Check the Instagram app settings, approved permissions and callback URL, then try again.",
            502,
        )
    return redirect(url_for("dashboard"))


@app.get("/dashboard")
def dashboard():
    connection = get_connection()
    if not connection:
        return redirect(url_for("index"))
    try:
        connection = refresh_token_if_needed(connection)
        profile = instagram_get(
            "/me",
            connection["access_token"],
            {"fields": "id,username,account_type,media_count,profile_picture_url"},
        )
    except (requests.RequestException, RuntimeError, ValueError):
        return render_message(
            "Reconnect your Instagram account",
            "The saved Instagram connection has expired or is no longer valid. Disconnect and connect again.",
            401,
        )

    media_warning = None
    media = []
    try:
        media_payload = instagram_get(
            "/me/media",
            connection["access_token"],
            {"fields": "id,caption,media_type,media_url,permalink,timestamp", "limit": "12"},
        )
        for item in media_payload.get("data", []):
            media.append({
                "media_type": item.get("media_type"),
                "caption": str(item.get("caption") or ""),
                "image_url": safe_https_url(item.get("media_url")),
                "permalink": safe_https_url(item.get("permalink")),
            })
    except (requests.RequestException, RuntimeError, ValueError):
        media_warning = "Profile connected, but Instagram did not return media for this request. Check the account's permissions and API access."

    return render_template_string(
        DASHBOARD_TEMPLATE,
        username=profile.get("username") or connection["username"],
        account_type=profile.get("account_type") or connection["account_type"],
        instagram_user_id=connection["instagram_user_id"],
        profile_picture_url=safe_https_url(profile.get("profile_picture_url")) or connection["profile_picture_url"],
        media_count=profile.get("media_count", connection["media_count"]),
        media=media,
        media_warning=media_warning,
        csrf_token=get_csrf_token(),
    )


def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.post("/disconnect")
def disconnect():
    expected = session.get("csrf_token", "")
    supplied = request.form.get("csrf_token", "")
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        abort(400)
    session_id = session.get("app_session_id")
    if session_id:
        delete_connection(session_id)
    session.clear()
    return redirect(url_for("index"))


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
