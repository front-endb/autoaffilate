"""Pinterest API v5 client: OAuth helper, list boards, create pin.
Without PINTEREST_ACCESS_TOKEN runs in dry-run mode (logs what WOULD be posted).

OAuth (одноразово, коли отримаєш апрув апки):
    python pinterest_client.py auth
відкриє URL авторизації; після редіректу встав code — скрипт обміняє його на
токен і покаже, що вписати в .env.
"""
import base64
import sys
from pathlib import Path

import requests

import config

API = "https://api.pinterest.com/v5"
MOCK = not config.PINTEREST_ACCESS_TOKEN


def _headers():
    return {"Authorization": f"Bearer {config.PINTEREST_ACCESS_TOKEN}"}


# ---------- OAuth ----------

def auth_url() -> str:
    return (
        "https://www.pinterest.com/oauth/"
        f"?client_id={config.PINTEREST_APP_ID}"
        f"&redirect_uri={config.PINTEREST_REDIRECT_URI}"
        "&response_type=code"
        "&scope=boards:read,boards:write,pins:read,pins:write"
    )


def exchange_code(code: str) -> dict:
    basic = base64.b64encode(
        f"{config.PINTEREST_APP_ID}:{config.PINTEREST_APP_SECRET}".encode()
    ).decode()
    resp = requests.post(
        f"{API}/oauth/token",
        headers={"Authorization": f"Basic {basic}"},
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.PINTEREST_REDIRECT_URI,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------- Boards ----------

def list_boards() -> list[dict]:
    if MOCK:
        return [{"id": "mock-board-1", "name": "Home Finds"},
                {"id": "mock-board-2", "name": "Desk Setup"}]
    resp = requests.get(f"{API}/boards", headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json().get("items", [])


def get_or_create_board(name: str) -> dict:
    for b in list_boards():
        if b["name"].lower() == name.lower():
            return b
    if MOCK:
        return {"id": f"mock-board-{name.lower().replace(' ', '-')}", "name": name}
    resp = requests.post(
        f"{API}/boards", headers=_headers(),
        json={"name": name, "privacy": "PUBLIC"}, timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------- Pins ----------

def create_pin(board_id: str, title: str, description: str,
               link: str, image_path: str) -> str:
    """Returns pin id ('dry-run' in mock mode)."""
    if MOCK:
        import ui
        ui.log("UPLOAD", f"[yellow](dry-run)[/yellow] pin -> {board_id} | "
                         f"{title[:60]} | {Path(image_path).name}")
        return "dry-run"

    img_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    resp = requests.post(
        f"{API}/pins",
        headers=_headers(),
        json={
            "board_id": board_id,
            "title": title[:100],
            "description": description[:800],
            "link": link,
            "media_source": {
                "source_type": "image_base64",
                "content_type": "image/jpeg",
                "data": img_b64,
            },
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["id"]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        if not config.PINTEREST_APP_ID:
            sys.exit("Спочатку заповни PINTEREST_APP_ID / PINTEREST_APP_SECRET у .env")
        print("Відкрий у браузері й авторизуйся:\n", auth_url())
        code = input("\nВстав code з redirect URL: ").strip()
        tokens = exchange_code(code)
        print("\nДодай у .env:")
        print(f"PINTEREST_ACCESS_TOKEN={tokens['access_token']}")
