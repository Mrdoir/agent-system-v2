"""
COMBINED RUNNER — Runs both dashboard (Flask) and manager (agents) in one process.
Use this as your Render Web Service start command: python run.py

This solves the "no open ports" error by running Flask on a port
while the manager runs in a background thread.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import threading
import time


def run_manager():
    """Run the agent manager in a background thread."""
    time.sleep(5)  # Let Flask start first
    try:
        from manager import main as manager_main
        manager_main()
    except Exception as e:
        print(f"[RUN] Manager error: {e}", flush=True)


def run_dashboard():
    """Run the Flask dashboard (blocks — this is the main thread)."""
    from dashboard import app
    port = int(os.environ.get("PORT", 10000))
    print(f"[RUN] Starting dashboard on port {port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    print("[RUN] ═══════════════════════════════════════════", flush=True)
    print("[RUN] AGENT RESEARCH HUB — Combined Runner", flush=True)
    print("[RUN] Dashboard + Manager in one process", flush=True)
    print("[RUN] ═══════════════════════════════════════════", flush=True)
    
    # Start manager in background thread
    manager_thread = threading.Thread(target=run_manager, daemon=True)
    manager_thread.start()
    
    # Start Flask in main thread (this binds the port Render needs)
    run_dashboard()
