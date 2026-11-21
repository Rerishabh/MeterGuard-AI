import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = r"C:\Users\risha\.gemini\antigravity\brain\513b349e-f6a4-4e82-9ee4-1958fc49fb79"
USER_DATA = r"C:\Users\risha\.gemini\temp-chrome-cdp"
PORT = 9222

pages = [
    ("audit_dashboard.png", "http://localhost:5173/#dashboard"),
    ("audit_live_monitoring.png", "http://localhost:5173/#live-monitoring"),
]

async def capture_all():
    # Start Chrome with remote debugging
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        f"--remote-debugging-port={PORT}",
        f"--user-data-dir={USER_DATA}",
        "--window-size=1920,1080",
    ]
    proc = subprocess.Popen(cmd)
    try:
        await asyncio.sleep(2)
        # Get websocket URL
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")
        data = json.loads(req.read().decode())
        browser_ws = data["webSocketDebuggerUrl"]

        async with websockets.connect(browser_ws, max_size=20*1024*1024) as ws:
            # Create a target page
            msg_id = 1
            await ws.send(json.dumps({"id": msg_id, "method": "Target.createTarget", "params": {"url": "about:blank"}}))
            res = json.loads(await ws.recv())
            target_id = res["result"]["targetId"]

            # Attach to target
            msg_id += 1
            await ws.send(json.dumps({"id": msg_id, "method": "Target.attachToTarget", "params": {"targetId": target_id, "flatten": True}}))
            res = json.loads(await ws.recv())
            session_id = res["params"]["sessionId"] if "params" in res else res["result"]["sessionId"]

            # Set viewport to 1920x1080
            msg_id += 1
            await ws.send(json.dumps({
                "id": msg_id,
                "sessionId": session_id,
                "method": "Emulation.setDeviceMetricsOverride",
                "params": {"width": 1920, "height": 1080, "deviceScaleFactor": 1, "mobile": False}
            }))
            await ws.recv()

            for filename, url in pages:
                print(f"Navigating to {url}...")
                msg_id += 1
                await ws.send(json.dumps({
                    "id": msg_id,
                    "sessionId": session_id,
                    "method": "Page.navigate",
                    "params": {"url": url}
                }))
                await ws.recv()

                # Wait 4.0 seconds for React to fetch /api/dashboard and render
                await asyncio.sleep(4.0)

                msg_id += 1
                await ws.send(json.dumps({
                    "id": msg_id,
                    "sessionId": session_id,
                    "method": "Page.captureScreenshot",
                    "params": {"format": "png"}
                }))

                # Wait for screenshot response
                while True:
                    resp = json.loads(await ws.recv())
                    if resp.get("id") == msg_id:
                        img_data = base64.b64decode(resp["result"]["data"])
                        out_path = os.path.join(OUTPUT_DIR, filename)
                        with open(out_path, "wb") as f:
                            f.write(img_data)
                        print(f" -> Saved {filename} ({len(img_data)} bytes)")
                        break

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(capture_all())
