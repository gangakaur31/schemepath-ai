#!/usr/bin/env python3
"""
Startup script for AVSAR.
Starts backend (FastAPI) and frontend (Streamlit) together.
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

processes = []

def start():
    print("Starting AVSAR...")
    print("=" * 50)

    # Start backend
    print("Starting backend on http://localhost:8000 ...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"],
        cwd=BACKEND,
        env={**os.environ, "PYTHONPATH": str(BACKEND)},
    )
    processes.append(backend_proc)
    time.sleep(3)

    # Start frontend
    print("Starting frontend on http://localhost:8501 ...")
    frontend_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501"],
        cwd=FRONTEND,
    )
    processes.append(frontend_proc)

    print("\nAVSAR is running:")
    print("   Backend  -> http://localhost:8000")
    print("   Frontend -> http://localhost:8501")
    print("   API Docs -> http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
            # Check if any process died
            for p in processes:
                if p.poll() is not None:
                    print("Process exited unexpectedly. Shutting down...")
                    stop()
                    sys.exit(1)
    except KeyboardInterrupt:
        stop()

def stop():
    print("\nShutting down AVSAR...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            p.kill()
    print("Stopped.")

if __name__ == "__main__":
    start()
