import httpx

from app.core.settings import settings

_BASE = "https://api.telegram.org/bot{token}/{method}"


def send_message(chat_id: int, text: str, parse_mode: str = "HTML") -> None:
    url = _BASE.format(token=settings.telegram_bot_token, method="sendMessage")
    httpx.post(
        url,
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        timeout=10,
    )


def send_photo(chat_id: int, image_bytes: bytes, caption: str = "") -> None:
    url = _BASE.format(token=settings.telegram_bot_token, method="sendPhoto")
    httpx.post(
        url,
        data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
        files={"photo": ("chart.png", image_bytes, "image/png")},
        timeout=20,
    )
