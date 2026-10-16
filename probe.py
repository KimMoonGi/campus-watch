import urllib.request, gzip, zlib
for ua in ["Mozilla/5.0 campus-watch",
           "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"]:
    for url in ["https://madrid.campusatleticodemadrid.com/"]:
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html", "Accept-Language": "es-ES,es;q=0.9"})
        try:
            r = urllib.request.urlopen(req, timeout=30)
            raw = r.read()
            print("UA", ua[:25], "status", r.status, "final", r.geturl(), "len", len(raw), "enc", r.headers.get("Content-Encoding"), "type", r.headers.get("Content-Type"))
            print("HEAD", raw[:400])
            low = raw.lower()
            print("navidad at", low.find(b"navidad"))
        except Exception as e:
            print("UA", ua[:25], "ERR", repr(e)[:300])
