"""One-off Google Calendar OAuth flow.

Run on a machine with a browser (``just auth-calendar``); the token is written to
``credentials/.google_calendar_token.json``, which the container mounts.
"""

from .data import TOKEN_FILE, run_interactive_auth

if __name__ == "__main__":
    run_interactive_auth()
    print(f"Saved Google Calendar token to {TOKEN_FILE}")
