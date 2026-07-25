import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.settings import settings
from app.lib.fd_image import render_fd_image
from app.lib.telegram import send_message, send_photo
from app.modules.fundamental.service import get_fundamental_report
from app.modules.telegram.handlers import handle_screen_args
from app.modules.telegram.task import run_screen_telegram

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


# ── Bot webhook ──────────────────────────────────────────────────────


@router.post("/webhook")
async def webhook(request: Request):
    data = await request.json()

    message = data.get("message") or data.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id: int = message["chat"]["id"]
    text: str = message.get("text", "")

    if str(chat_id) != str(settings.telegram_allowed_chat_id):
        return {"ok": True}

    if not text.startswith("/"):
        return {"ok": True}

    parts = text.strip().lstrip("/").split()
    command = parts[0].split("@")[0].lower() if parts else ""
    args = parts[1:]

    if command == "fd":
        await _handle_fd(chat_id, args)

    elif command == "screen":
        signals, error = handle_screen_args(args)
        if error:
            send_message(chat_id, error)
        else:
            send_message(
                chat_id, f"Scanning for <b>{', '.join(s.upper() for s in signals)}</b>…"
            )
            run_screen_telegram.delay(chat_id, signals)

    elif command == "help":
        send_message(
            chat_id,
            (
                "<b>Available commands</b>\n\n"
                "<code>/fd TICKER</code> — fundamental snapshot\n"
                "<code>/screen ketat|superketat|theone|kamehameha</code> — screen IDX tickers\n"
                "<code>/help</code> — show this message"
            ),
        )

    return {"ok": True}


async def _handle_fd(chat_id: int, args: list[str]) -> None:
    if not args:
        send_message(
            chat_id, "Usage: <code>/fd TICKER</code> — e.g. <code>/fd BBRI</code>"
        )
        return
    report = get_fundamental_report(args[0].upper())
    if not report.metrics:
        send_message(chat_id, f"<b>{report.symbol}</b>\n{report.reading}")
    else:
        send_photo(chat_id, render_fd_image(report))


# ── Webhook setup ────────────────────────────────────────────────────


class SetupRequest(BaseModel):
    url: str


@router.post("/setup-webhook")
def setup_webhook(body: SetupRequest):
    api_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"
    res = httpx.post(api_url, json={"url": body.url})
    return res.json()
