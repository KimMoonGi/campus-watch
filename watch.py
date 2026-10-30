"""Atlético de Madrid Christmas campus: sold-out watcher (Majadahonda).

Hayden is already registered, so this no longer watches for new campus
text. It only answers one question: when does the Majadahonda Generation
Christmas campus (28-31 Dec, half day, 6-11) fill up?

Every few hours it adds that campus to a fresh, throwaway cart on the
official shop and reads the cart page. If the item lands in the cart, places
are still open. If the shop refuses it (error notice / empty cart), the
campus is full. A phone push via ntfy is sent only when that status changes.
"""
import html
import http.cookiejar
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

ADD_URL = (
    "https://madrid.campusatleticodemadrid.com/?wre-add-to-cart=152&quantity=1"
    "&attribute_pa_program_modality=media-jornada"
    "&attribute_pa_program_location=majadahonda"
    "&attribute_pa_program_group=general"
    "&attribute_pa_program_week=diciembre-28-31"
    "&attribute_pa_program_age=6-a-11"
)
PAGE_URL = "https://madrid.campusatleticodemadrid.com/campus-navidad/"
STATE_FILE = "state.json"
TOPIC = os.environ.get("NTFY_TOPIC", "")
UA = ("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36")


def check():
    """Return (status, detail): status is 'open', 'full' or 'unknown'."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(ADD_URL, headers={
        "User-Agent": UA, "Accept": "text/html", "Accept-Language": "es-ES,es;q=0.9"})
    with opener.open(req, timeout=40) as r:
        raw = r.read().decode("utf-8", errors="ignore")
    notices = [re.sub(r"<[^>]+>|\s+", " ", html.unescape(m)).strip()
               for m in re.findall(r'woocommerce-error[^>]*>(.*?)</(?:ul|div)>', raw, re.S)]
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))
    in_cart = "Location: Majadahonda" in text or "Localidad: Majadahonda" in text
    if in_cart and not notices:
        return "open", "added to cart"
    if notices:
        return "full", notices[0][:200]
    if re.search(r"carrito est[aá] vac[ií]o|agotad|completo|sin plazas|no quedan", text, re.I):
        return "full", "cart empty / sold-out wording"
    return "unknown", text[:200]


def push(title, message, priority=5):
    if not TOPIC:
        print("NTFY_TOPIC not set; skipping push:", title)
        return
    body = {"topic": TOPIC, "title": title, "message": message,
            "priority": priority, "tags": ["soccer"], "click": PAGE_URL}
    req = urllib.request.Request(
        "https://ntfy.sh", data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=30).read()


def main():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    for old in ("pages", "seen", "seen_v2", "seen_v3"):  # old text-watch formats
        state.pop(old, None)
    now = datetime.now(timezone.utc)
    kst = now.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    try:
        status, detail = check()
    except Exception as e:  # site down: try again next run
        print("check failed:", e)
        status, detail = "unknown", str(e)[:200]
    print(f"[majadahonda-xmas] {status}: {detail}")

    prev = state.get("status")
    if status in ("open", "full"):
        if status != prev:
            state.setdefault("history", []).append({"at": kst, "status": status, "detail": detail})
            if prev == "open" and status == "full":
                push("Majadahonda Christmas campus is FULL",
                     f"Sold out detected at {kst} (last seen open: {state.get('last_open', '?')}). {detail}")
            elif prev == "full" and status == "open":
                push("Majadahonda Christmas campus has places again",
                     f"Places reopened at {kst}.", priority=3)
        state["status"] = status
        if status == "open":
            state["last_open"] = kst
    state["last_check"] = kst
    # weekly keepalive so GitHub doesn't pause the schedule after 60 idle days
    state["week"] = now.strftime("%G-W%V")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    sys.exit(main())
