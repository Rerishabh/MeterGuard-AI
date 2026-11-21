import subprocess
import time
import os

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = r"C:\Users\risha\.gemini\antigravity\brain\513b349e-f6a4-4e82-9ee4-1958fc49fb79"
USER_DATA = r"C:\Users\risha\.gemini\temp-chrome"

pages = [
    ("audit_dashboard.png", "http://localhost:5173/#dashboard"),
    ("audit_live_monitoring.png", "http://localhost:5173/#live-monitoring"),
    ("audit_ai_detection.png", "http://localhost:5173/#ai-detection"),
    ("audit_meter_network.png", "http://localhost:5173/#meter-network"),
    ("audit_meter_locations.png", "http://localhost:5173/#meter-locations"),
    ("audit_alerts_logs.png", "http://localhost:5173/#alerts-logs"),
    ("audit_settings.png", "http://localhost:5173/#settings"),
]

for filename, url in pages:
    out_path = os.path.join(OUTPUT_DIR, filename)
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        f"--user-data-dir={USER_DATA}",
        f"--screenshot={out_path}",
        "--window-size=1920,1080",
        url,
    ]
    print(f"Capturing {filename} from {url}...")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    exists = os.path.exists(out_path)
    size = os.path.getsize(out_path) if exists else 0
    print(f" -> Result exists={exists}, size={size} bytes")

print("Done capturing screenshots.")
