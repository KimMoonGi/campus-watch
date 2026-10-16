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
import urllib.request
from datetime import datetime, timezone

URLS = {
    "campus-site": "https://campusatleticodemadrid.com/",
    "majadahonda": "https://www.atleticodemadrid.com/atm/ciudad-deportiva-wanda-de-majadahonda",
    "alcala": "https://www.atleticodemadrid.com/atm/centro-deportivo-wanda-alcala-de-henares",
}
KEYWORDS = ("navidad", "christmas", "clinic")
SIGNALS = ("2026", "diciembre", "december", "inscripci", "registration")
STATE_FILE = "state.json"
TOPIC = os.environ.get("NTFY_TOPIC", "")


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 campus-watch"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", errors="ignore")
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))
    return re.sub(r"\s+", " ", text).strip()


def relevant_snippets(text):
    low = text.lower()
    out = []
    for kw in KEYWORDS:
        for m in re.finditer(kw, low):
            out.append(text[max(0, m.start() - 150): m.end() + 250])
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
    first_run = "pages" not in state
    pages = state.setdefault("pages", {})

    for name, url in URLS.items():
        try:
            snippets = relevant_snippets(fetch_text(url))
        except Exception as e:  # site down or blocked: try again next run
            print(f"[{name}] fetch failed: {e}")
            continue
        joined = " | ".join(snippets)
        digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        old = pages.get(name)
        pages[name] = digest
        if first_run or old == digest:
            print(f"[{name}] no change")
            continue
        if any(s in joined.lower() for s in SIGNALS):
            preview = (snippets[0] if snippets else "")[:300]
            push("Atleti campus update - check now!",
                 f"[{name}] Christmas campus page changed.\n{preview}", url)
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
