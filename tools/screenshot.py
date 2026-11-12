"""Open a Streamlit page in a real browser, wake it if it sleeps, and screenshot it once rendered.

Two jobs share this script, because both need a browser that really runs the page:

- **The after-push check** (CLAUDE.md, Session Workflow) looks at the live app. A plain headless
  `--screenshot` doesn't work for it: `--virtual-time-budget` runs the browser's clock ahead, but
  Streamlit draws over a websocket in real time, so the shot catches the loading skeleton. This
  waits, in real time, until the page text contains a marker, then captures the viewport.
- **The keep-alive** (.github/workflows/keepalive.yml) visits the live app on a schedule.
  Streamlit Community Cloud puts an app to sleep after 12 hours without traffic, and a plain HTTP
  GET neither counts as a visit nor wakes it. If the "gone to sleep" page shows, this clicks its
  wake-up button and waits for the app to boot.

Exit code 0 if the marker was found, 1 if not, so a scheduled run fails loudly when the app is down.

Usage (dev tool and CI job, not part of the app):
    python tools/screenshot.py <url> <out.png> <must_contain> [width] [height] [timeout_s]
    python tools/screenshot.py https://gpfootball-analytics-portfolio.streamlit.app/ home.png "Scout by data"

Needs Chrome (its default install path, `google-chrome`/`chromium` on PATH, or the `CHROME`
environment variable) and tornado's websocket client (installed with Streamlit). Edge won't do:
mid-update, its launcher hands the call off and exits without a file (2026-10-17).
"""
import asyncio, base64, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from tornado.websocket import websocket_connect

CHROME_CANDIDATES = (
    os.environ.get("CHROME"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    shutil.which("google-chrome"),
    shutil.which("chromium"),
    shutil.which("chromium-browser"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)
PORT = 9333
SLEEP_MARKER = "gone to sleep"
WAKE_TIMEOUT_S = 600  # a woken app reinstalls its requirements before it draws anything

# Streamlit Community Cloud serves the app inside a same-origin iframe, under a frame of its own
# that holds only the "Hosted with Streamlit" badge. The top document's text is therefore empty
# on the live app (a local `streamlit run` has no such frame), so read the iframes too.
PAGE_TEXT_JS = """(() => {
    const texts = [document.body ? document.body.innerText : ''];
    for (const frame of document.querySelectorAll('iframe')) {
        try { texts.push(frame.contentDocument.body.innerText); } catch (error) { /* cross-origin */ }
    }
    return texts.join('\\n');
})()"""
WAKE_CLICK_JS = """(() => {
    const button = [...document.querySelectorAll('button')].find(b => /get this app back up/i.test(b.innerText));
    if (button) { button.click(); return true; }
    return false;
})()"""


def find_chrome():
    """The first Chrome that exists on this machine, or a clear error naming where it looked."""
    for path in CHROME_CANDIDATES:
        if path and os.path.exists(path):
            return path
    raise SystemExit("Chrome not found. Set the CHROME environment variable to its executable.")


async def visit(ws_url, url, out, marker, width, height, timeout):
    """Load `url`, wake the app if it sleeps, wait for `marker`, screenshot. Returns found?"""
    ws = await websocket_connect(ws_url, max_message_size=200 * 2**20)
    ids = iter(range(1, 10**6))

    async def call(method, **params):
        msg_id = next(ids)
        await ws.write_message(json.dumps({"id": msg_id, "method": method, "params": params}))
        while True:
            reply = json.loads(await ws.read_message())
            if reply.get("id") == msg_id:
                return reply.get("result", {})

    async def evaluate(expression):
        result = await call("Runtime.evaluate", expression=expression)
        return result.get("result", {}).get("value")

    await call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
    await call("Page.navigate", url=url)
    start, text, woken = time.time(), "", False
    while time.time() - start < timeout:
        await asyncio.sleep(2)
        text = await evaluate(PAGE_TEXT_JS) or ""
        if marker in text and "Running..." not in text:
            break
        if not woken and SLEEP_MARKER in text and await evaluate(WAKE_CLICK_JS):
            woken = True
            timeout = max(timeout, WAKE_TIMEOUT_S)
            print(f"The app was asleep: clicked its wake-up button after {time.time() - start:.0f}s.")
    await asyncio.sleep(2)  # let charts and fonts settle
    shot = await call("Page.captureScreenshot", format="png")
    with open(out, "wb") as f:
        f.write(base64.b64decode(shot["data"]))
    found = marker in text
    state = "woken from sleep" if woken else "already awake"
    print(f"found ({state})" if found else "MARKER NOT FOUND", f"after {time.time() - start:.0f}s ->", out)
    print("address:", await evaluate("location.href"))  # shows whether the page rewrote its own link
    print(" ".join(text.split())[:300])
    return found


def main():
    url, out, marker = sys.argv[1], sys.argv[2], sys.argv[3]
    width = int(sys.argv[4]) if len(sys.argv) > 4 else 1900
    height = int(sys.argv[5]) if len(sys.argv) > 5 else 1500
    timeout = float(sys.argv[6]) if len(sys.argv) > 6 else 120
    flags = ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run"]
    if sys.platform.startswith("linux"):
        flags.append("--no-sandbox")  # CI runners restrict the user namespaces Chrome's sandbox needs
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        chrome = subprocess.Popen(
            [find_chrome(), *flags, f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            ws_url = None
            for _ in range(100):
                try:
                    pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                    ws_url = next(p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page")
                    break
                except Exception:
                    time.sleep(0.2)
            if ws_url is None:
                raise SystemExit("Chrome started but its DevTools port never answered.")
            found = asyncio.run(visit(ws_url, url, out, marker, width, height, timeout))
        finally:
            chrome.terminate()
            chrome.wait(timeout=10)
    sys.exit(0 if found else 1)


if __name__ == "__main__":
    main()
