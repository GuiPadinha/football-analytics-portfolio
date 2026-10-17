"""Screenshot a Streamlit page once it has really rendered, via Chrome's DevTools protocol.

The after-push check (CLAUDE.md, Session Workflow) looks at the live app, and a plain headless
`--screenshot` doesn't work for it: `--virtual-time-budget` runs the browser's clock ahead, but
Streamlit draws over a websocket in real time, so the shot catches the loading skeleton. This
waits, in real time, until the page text contains a marker, then captures the viewport. Edge
won't do either: mid-update, its launcher hands the call off and exits without a file (2026-10-17).

Usage (dev tool, not part of the app or CI):
    python tools/screenshot.py <url> <out.png> <must_contain> [width] [height] [timeout_s]
    python tools/screenshot.py https://gpfootball-analytics-portfolio.streamlit.app/ home.png "Scout by data"

Needs Chrome at its default path, and tornado's websocket client (installed with Streamlit).
"""
import asyncio, base64, json, subprocess, sys, tempfile, time, urllib.request
from tornado.websocket import websocket_connect

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9333
url, out, marker = sys.argv[1], sys.argv[2], sys.argv[3]
width, height = int(sys.argv[4]) if len(sys.argv) > 4 else 1900, int(sys.argv[5]) if len(sys.argv) > 5 else 1500
timeout = float(sys.argv[6]) if len(sys.argv) > 6 else 120


async def main(ws_url):
    ws = await websocket_connect(ws_url, max_message_size=200 * 2**20)
    ids = iter(range(1, 10**6))

    async def call(method, **params):
        msg_id = next(ids)
        await ws.write_message(json.dumps({"id": msg_id, "method": method, "params": params}))
        while True:
            reply = json.loads(await ws.read_message())
            if reply.get("id") == msg_id:
                return reply.get("result", {})

    await call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
    await call("Page.navigate", url=url)
    start, text = time.time(), ""
    while time.time() - start < timeout:
        await asyncio.sleep(2)
        result = await call("Runtime.evaluate", expression="document.body ? document.body.innerText : ''")
        text = result.get("result", {}).get("value", "") or ""
        if marker in text and "Running..." not in text:
            break
    await asyncio.sleep(2)  # let charts and fonts settle
    shot = await call("Page.captureScreenshot", format="png")
    with open(out, "wb") as f:
        f.write(base64.b64decode(shot["data"]))
    print("found" if marker in text else "MARKER NOT FOUND", f"after {time.time() - start:.0f}s ->", out)
    print(" ".join(text.split())[:300])


with tempfile.TemporaryDirectory() as profile:
    chrome = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                               f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                ws_url = next(p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        asyncio.run(main(ws_url))
    finally:
        chrome.terminate()
        chrome.wait(timeout=10)
