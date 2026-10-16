import urllib.request, re, html
req = urllib.request.Request("https://madrid.campusatleticodemadrid.com/", headers={"User-Agent": "Mozilla/5.0 campus-watch"})
raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="ignore")
print("raw", len(raw))
a = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
print("after script strip", len(a))
for m in list(re.finditer(r"(?is)<(script|style|noscript)[^>]*>", raw))[:3]:
    print("open tag", repr(raw[m.start():m.start()+80]))
b = re.sub(r"(?s)<[^>]+>", " ", a)
print("after tag strip", len(b), repr(re.sub(r"\s+"," ",b)[:200]))
i = raw.lower().find("navidad"); print("ctx", repr(raw[i-300:i+100]))
