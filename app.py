"""Gold & Silver Prices India - Whop paid-members-only app.

Whop opens this app inside an iframe and sends a signed token in the
x-whop-user-token header. We verify it, ask Whop whether that user has paid
access to the experience, and only then return the price page.
"""
import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from whop_sdk import Whop, WhopEnvironment
from whop_sdk.lib.verify_user_token import verify_user_token

APP_ID = os.environ["WHOP_APP_ID"]  # looks like app_xxxxxxxx
client = Whop(
    token=os.environ["WHOP_API_KEY"],
    environment=(
        WhopEnvironment.PRODUCTION
        if os.environ.get("WHOP_ENVIRONMENT") == "production"
        else WhopEnvironment.SANDBOX
    ),
)

# The paid page is read into memory and is NOT served as a public file.
PAGE = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('goldsilver')

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def message(title: str, text: str, status: int) -> HTMLResponse:
    html = (
        "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>"
        "<body style='font-family:Arial;background:#0b1a33;color:#fff;text-align:center;padding:48px 16px'>"
        f"<h2 style='color:#f5c84a'>{title}</h2><p>{text}</p></body>"
    )
    return HTMLResponse(html, status_code=status)


@app.get("/")
def home():
    return message("Gold & Silver Prices India", "Open this app from inside Whop.", 200)


@app.get("/health")
def health():
    return {"ok": True}


# Plain "def" (not async): the Whop SDK calls below are blocking.
@app.get("/experiences/{experience_id}")
def experience(experience_id: str, request: Request):
    try:
        user_id = verify_user_token(request.headers, app_id=APP_ID).user_id
    except Exception:
        log.exception('verify_user_token failed')
        return message("Please open this inside Whop", "We could not verify who you are.", 401)

    try:
        access = client.users.check_access(resource_id=experience_id, id=user_id)
    except Exception:
        log.exception('check_access failed (experience_id=%s, user_id=%s)', experience_id, user_id)
        return message("Something went wrong", "Could not check your access. Please try again.", 502)

    if not access.has_access:
        return message("Members only", "Buy access on Whop to use the live gold and silver price app.", 403)

    return HTMLResponse(PAGE, headers={"Cache-Control": "no-store"})
