"""
whoop_auth.py
Handles the OAuth 2.0 flow to get an access token + refresh token from WHOOP.

Setup before running:
1. Go to developer-dashboard.whoop.com, sign in, create an App.
2. WHOOP requires the Redirect URL to be https:// (or a custom scheme) --
   plain http://localhost is NOT accepted. Since we don't have a hosted
   server, register: https://localhost:8000/callback
   You'll never actually need anything listening there -- see below.
3. WHOOP also requires a Privacy Policy URL. For a personal project, a
   single markdown page on GitHub Pages describing what data you access
   and that it isn't shared satisfies this.
4. Copy your Client ID and Client Secret into a `.env` file (see .env.example).

Run:
    python3 whoop_auth.py

This opens your browser to WHOOP's authorization page. After you approve,
WHOOP redirects to your (non-existent) https://localhost:8000/callback URL --
the page will fail to load, but the browser's address bar will contain the
full URL with a `code=...` parameter in it. Copy that whole URL and paste
it back into the terminal when prompted. Tokens are saved to `tokens.json`.
Do NOT commit tokens.json or .env to git -- both are listed in .gitignore.
"""
import os
import json
import urllib.parse
import webbrowser
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["WHOOP_CLIENT_ID"]
CLIENT_SECRET = os.environ["WHOOP_CLIENT_SECRET"]
REDIRECT_URI = "https://localhost:8000/callback"
AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
SCOPES = "read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement offline"


def get_auth_code():
    state = "xk3921kd"  # any random 8+ char string
    query = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
    })
    url = f"{AUTH_URL}?{query}"
    print(f"Opening browser for WHOOP authorization...\n{url}\n")
    webbrowser.open(url)

    print(
        "\nAfter you approve access, the browser will try to load\n"
        f"{REDIRECT_URI} and fail to connect -- that's expected.\n"
        "Copy the FULL url from the address bar at that point (it will\n"
        "contain '?code=...') and paste it below.\n"
    )
    pasted = input("Paste the redirected URL here: ").strip()
    parsed = urllib.parse.urlparse(pasted)
    params = urllib.parse.parse_qs(parsed.query)

    if "code" not in params:
        raise RuntimeError("No 'code' parameter found in the pasted URL.")
    if params.get("state", [None])[0] != state:
        raise RuntimeError("State mismatch -- possible CSRF or stale link. Try again.")

    return params["code"][0]


def exchange_code_for_token(code):
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
    })
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token):
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()


def save_tokens(token_data):
    with open("tokens.json", "w") as f:
        json.dump(token_data, f, indent=2)
    print("Saved tokens to tokens.json")


def load_tokens():
    if not os.path.exists("tokens.json"):
        return None
    with open("tokens.json") as f:
        return json.load(f)


def get_valid_access_token():
    """Returns a valid access token, refreshing if a token file already exists."""
    tokens = load_tokens()
    if tokens and "refresh_token" in tokens:
        try:
            new_tokens = refresh_access_token(tokens["refresh_token"])
            save_tokens(new_tokens)
            return new_tokens["access_token"]
        except requests.HTTPError:
            print("Refresh failed, falling back to full OAuth flow.")

    code = get_auth_code()
    token_data = exchange_code_for_token(code)
    save_tokens(token_data)
    return token_data["access_token"]


if __name__ == "__main__":
    token = get_valid_access_token()
    print(f"\nAccess token acquired (first 15 chars): {token[:15]}...")