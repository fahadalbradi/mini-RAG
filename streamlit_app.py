"""One-command demo: `streamlit run streamlit_app.py` from the repository root.

Starts the FastAPI backend in the background if it isn't already running,
then runs the real app in source/streamlit_app.py.
"""
import os
import runpy
import socket
import subprocess
import sys
import time

import streamlit as st

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(ROOT_DIR, "source")
API_HOST, API_PORT = "127.0.0.1", 8000

def api_is_up():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((API_HOST, API_PORT)) == 0

@st.cache_resource(show_spinner="Starting the mini-RAG API…")
def start_api():
    """Runs once per Streamlit server; the API stops when Streamlit stops."""
    if api_is_up():
        return None  # started separately, e.g. `uvicorn main:app --reload`

    log_file = open(os.path.join(ROOT_DIR, "api.log"), "w")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", API_HOST, "--port", str(API_PORT)],
        cwd=SOURCE_DIR, stdout=log_file, stderr=subprocess.STDOUT,
    )
    for _ in range(60):
        if api_is_up() or process.poll() is not None:
            break
        time.sleep(0.5)
    return process

if os.getenv("MINIRAG_API_URL") is None:  # only auto-start the local API
    start_api()

runpy.run_path(os.path.join(SOURCE_DIR, "streamlit_app.py"), run_name="__main__")
