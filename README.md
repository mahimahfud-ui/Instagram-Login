# IG Insights — Official Instagram Connection

This app uses Meta's Instagram API with Instagram Login. Users are redirected to Instagram for consent; this app does not collect Instagram passwords.

## Supported account types

Instagram Business and Creator (professional) accounts. Personal accounts are not supported by this API.

## Meta app setup

1. Create or open an app in the Meta for Developers dashboard.
2. Add Instagram API with Instagram Login / Instagram Business Login.
3. Configure Business Login and copy its Instagram-specific App ID and App Secret. Do not substitute unrelated Facebook app credentials if Meta shows a separate Instagram credential pair.
4. Add this exact callback URL to Valid OAuth Redirect URIs:
   https://YOUR_PUBLIC_HOST/auth/instagram/callback
5. Start with instagram_business_basic. Add further scopes only when the feature and Meta app review/access level require them.

## Hosting environment variables

Set these in the hosting provider's secret/environment settings. Do not commit secrets to Git.

| Variable | Required | Description |
|---|---:|---|
| FLASK_SECRET_KEY | Yes | Long random secret used to sign browser sessions and derive the at-rest token encryption key |
| INSTAGRAM_APP_ID | Yes | Instagram Business Login app/client ID shown in Meta |
| INSTAGRAM_APP_SECRET | Yes | Instagram Business Login app secret |
| INSTAGRAM_REDIRECT_URI | Yes | Exact HTTPS callback registered in Meta |
| DATABASE_URL | Production | Persistent PostgreSQL URL. Render postgres:// and postgresql:// forms are normalized automatically |
| INSTAGRAM_SCOPES | No | Comma-separated scopes; default instagram_business_basic |
| SESSION_COOKIE_SECURE | No | Defaults to true; set false only for local HTTP development |

Generate a strong Flask secret by running: python -c "import secrets; print(secrets.token_urlsafe(48))"

Use a persistent PostgreSQL database in production. The SQLite fallback is for local development only; Render's ephemeral filesystem is not suitable for permanent token storage. Access tokens are encrypted before storage and are never sent to browser JavaScript or printed to logs.

## Run locally

1. Create a Python virtual environment.
2. Activate it.
3. Install requirements.txt.
4. Set FLASK_SECRET_KEY to a long random value.
5. Set SESSION_COOKIE_SECURE=false only for local HTTP development.
6. Set INSTAGRAM_APP_ID and INSTAGRAM_APP_SECRET using your Instagram Business Login credentials.
7. Set INSTAGRAM_REDIRECT_URI to an HTTPS callback reachable by Meta, and register the exact same URL in Meta.
8. Run python app.py.

The callback must be reachable through HTTPS and match the URI registered in Meta exactly. The app cannot complete a real connection until Meta credentials, account eligibility, permissions and callback settings are configured.

## Render

Build command: pip install -r requirements.txt

Start command: gunicorn --workers 2 --bind 0.0.0.0:$PORT app:app

Add the variables above and attach a persistent PostgreSQL database before enabling real user connections.

## What the official API can show

The dashboard displays the connected professional account's available profile fields and recent media. The API does not provide a named list of profile visitors, people who blocked the account, or people who unfollowed the account. The old random-number dashboard and password-capturing login have been removed.

## Security

- OAuth state is validated on callback.
- Instagram authorization happens on instagram.com.
- Tokens are encrypted in the database; only a random server-side session identifier is held in the signed browser cookie.
- No password, authorization code, app secret, or access token is logged.
- Disconnect deletes the stored token record for the current browser session.
