from flask import Flask, Response, stream_with_context
import subprocess
import threading
import requests
import os

app = Flask(__name__)

# -------------------- 🎯 Run Streamlit as a Background Process --------------------
def run_streamlit():
    """Run the Streamlit app in the background."""
    streamlit_cmd = [
        "streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"
    ]
    subprocess.Popen(streamlit_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Start Streamlit in a background thread
thread = threading.Thread(target=run_streamlit)
thread.daemon = True
thread.start()

# -------------------- 🔥 Proxy Requests to Streamlit --------------------
@app.route("/dashboard/<path:path>", methods=["GET", "POST"])
def streamlit_proxy(path):
    """Proxy requests to the Streamlit server"""
    streamlit_url = f"http://localhost:8501/{path}"
    response = requests.request(
        method=request.method,
        url=streamlit_url,
        headers={key: value for key, value in request.headers if key != "Host"},
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False,
    )

    excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
    headers = [(name, value) for name, value in response.raw.headers.items() if name.lower() not in excluded_headers]

    return Response(response.content, response.status_code, headers)

@app.route("/")
def home():
    """Serve a default page with a link to the dashboard"""
    return """
    <html>
    <head><title>Flask + Streamlit App</title></head>
    <body>
        <h1>🏡 Welcome to Flask + Streamlit!</h1>
        <p><a href="/dashboard">Go to Dashboard</a></p>
    </body>
    </html>
    """

@app.route("/dashboard")
def streamlit_dashboard():
    """Serve the main Streamlit page via Flask"""
    return streamlit_proxy("")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
