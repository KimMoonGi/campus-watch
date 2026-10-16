"""Atlético de Madrid Christmas campus watcher.

Runs every 5 minutes on GitHub Actions. Fetches the campus pages, pulls out
the text around Christmas-campus keywords, and sends a phone push via ntfy
when that text changes and mentions 2026 / December.
"""
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

URLS = {
    # Madrid campus site (official, has the "Navidad 2026" section)
    "madrid-home": "https://madrid.campusatleticodemadrid.com/",
    "madrid-majadahonda": "https://madrid.campusatleticodemadrid.com/generation-majadahonda/",
    "madrid-majadahonda-venue": "https://madrid.campusatleticodemadrid.com/centro-deportivo-deportivo-majadahonda/",
    "madrid-alcala": "https://madrid.campusatleticodemadrid.com/generation-alcala-de-henares/",
    # Global hub and the club's own Majadahonda page (secondary)
    "campus-site": "https://campusatleticodemadrid.com/",
    "majadahonda": "https://www.atleticodemadrid.com/atm/ciudad-deportiva-wanda-de-majadahonda",
}
KEYWORDS = ("navidad", "christmas", "clinic")
SIGNALS = ("2026", "diciembre", "december", "inscripci", "registration")
# other-city campuses rotate through the site banner; ignore them
OTHER_CITIES = ("marbella", "bogot", "colombia", "lima", "per\u00fa", "peru", "miami", "dublin", "m\u00e9xico", "mexico")
STATE_FILE = "state.json"
TOPIC = os.environ.get("NTFY_TOPIC", "")


def fetch_text(url, tries=3):
    """Page text with scripts/styles/tags removed. Retries empty responses."""
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36",
            "Accept": "text/html", "Accept-Language": "es-ES,es;q=0.9"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", errors="ignore")
        raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
        text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) >= 200:
            return text
        last = len(text)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"page came back empty ({last} chars)")


def relevant_snippets(text):
    """Short windows of text around each Christmas-campus keyword."""
    low = text.lower()
    out = []
    for kw in KEYWORDS:
        for m in re.finditer(kw, low):
            w = text[max(0, m.start() - 80): m.end() + 120].strip()
            if w not in out:
                out.append(w)
    return out


def push(title, message, url=None, priority=5):
    if not TOPIC:
        print("NTFY_TOPIC not set; skipping push:", title)
        return
    body = {"topic": TOPIC, "title": title, "message": message,
            "priority": priority, "tags": ["soccer"]}
    if url:
        body["click"] = url
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
    first_run = not ({"pages", "seen", "seen_v2", "seen_v3"} & state.keys())
    state.pop("pages", None)  # old hash-based format
    for old_key in ("seen", "seen_v2"):  # earlier formats
        state.pop(old_key, None)
    seen_all = state.setdefault("seen_v3", {})

    for name, url in URLS.items():
        try:
            text = fetch_text(url)
            snippets = relevant_snippets(text)
            if os.environ.get("DEBUG"):
                print(f"[{name}] DEBUG len={len(text)} head={text[:300]!r}")
                i = text.lower().find("navidad")
                print(f"[{name}] DEBUG navidad_at={i} ctx={text[max(0,i-100):i+150]!r}")
        except Exception as e:  # site down or blocked: try again next run
            print(f"[{name}] fetch failed: {e}")
            continue
        # Remember every snippet ever seen, so rotating banners or reordered
        # blocks don't re-trigger; alert only on genuinely new text.
        seen = seen_all.get(name)
        current = {hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]: s for s in snippets}
        if seen is None:
            seen_all[name] = sorted(current)
            print(f"[{name}] baseline saved ({len(current)} snippets)")
            continue
        new = [s for h, s in current.items() if h not in seen]
        seen_all[name] = sorted(set(seen) | set(current))[-500:]
        if not new:
            print(f"[{name}] no change")
            continue
        for s in new:
            print(f"[{name}] NEW: {s}")
        hits = [s for s in new if any(sig in s.lower() for sig in SIGNALS)
                and not any(c in s.lower() for c in OTHER_CITIES)]
        if hits:
            push("Atleti campus update - check now!",
                 f"[{name}] New Christmas campus text:\n{hits[0][:300]}", url)
            print(f"[{name}] CHANGED -> pushed")

    if first_run:
        push("campus-watch started",
             "Monitoring Atletico Christmas campus pages every ~5 min.", priority=3)

    # weekly keepalive so GitHub doesn't pause the schedule after 60 idle days
    state["week"] = datetime.now(timezone.utc).strftime("%G-W%V")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    sys.exit(main())
