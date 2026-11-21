import asyncio
import base64
import json
import os
import subprocess
import urllib.request
import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = r"C:\Users\risha\.gemini\antigravity\brain\513b349e-f6a4-4e82-9ee4-1958fc49fb79"
USER_DATA = r"C:\Users\risha\.gemini\temp-chrome-cdp"
PORT = 9222

async def capture_scrolled():
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
        req = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version")
        data = json.loads(req.read().decode())
        browser_ws = data["webSocketDebuggerUrl"]

        async with websockets.connect(browser_ws, max_size=20*1024*1024) as ws:
            msg_id = 1
            await ws.send(json.dumps({"id": msg_id, "method": "Target.createTarget", "params": {"url": "about:blank"}}))
            res = json.loads(await ws.recv())
            target_id = res["result"]["targetId"]

            msg_id += 1
            await ws.send(json.dumps({"id": msg_id, "method": "Target.attachToTarget", "params": {"targetId": target_id, "flatten": True}}))
            res = json.loads(await ws.recv())
            session_id = res["params"]["sessionId"] if "params" in res else res["result"]["sessionId"]

            # Set viewport to 1920x3000 to capture full scrollable page
            msg_id += 1
            await ws.send(json.dumps({
                "id": msg_id,
                "sessionId": session_id,
                "method": "Emulation.setDeviceMetricsOverride",
                "params": {"width": 1920, "height": 3000, "deviceScaleFactor": 1, "mobile": False}
            }))
            await ws.recv()

            url = "http://localhost:5173/#ai-detection"
            msg_id += 1
            await ws.send(json.dumps({
                "id": msg_id,
                "sessionId": session_id,
                "method": "Page.navigate",
                "params": {"url": url}
            }))
            await ws.recv()
            await asyncio.sleep(4.0)

            msg_id += 1
            await ws.send(json.dumps({
                "id": msg_id,
                "sessionId": session_id,
                "method": "Page.captureScreenshot",
                "params": {"format": "png", "captureBeyondViewport": True}
            }))

            while True:
                resp = json.loads(await ws.recv())
                if resp.get("id") == msg_id:
                    img_data = base64.b64decode(resp["result"]["data"])
                    out_path = os.path.join(OUTPUT_DIR, "audit_investigation_brief.png")
                    with open(out_path, "wb") as f:
                        f.write(img_data)
                    print(f"Saved audit_investigation_brief.png ({len(img_data)} bytes)")
                    break
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    asyncio.run(capture_scrolled())
