"""Compatibility entry point.

The old standalone login form captured Instagram passwords and printed them to
server logs. That implementation has been removed. All authentication now
uses the official Instagram OAuth flow in app.py.
"""
import os

from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
