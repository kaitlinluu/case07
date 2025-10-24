from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient, ContentSettings
import os
from datetime import datetime
import re

# ---------- CONFIG ----------
STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL", "https://<acct>.blob.core.windows.net")
IMAGES_CONTAINER = os.getenv("IMAGES_CONTAINER", "lanternfly-images-gyvmon83")
AZURE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# ---------- AZURE BLOB CLIENT ----------
bsc = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
cc = bsc.get_container_client(IMAGES_CONTAINER)

# ---------- FLASK APP ----------
app = Flask(__name__)

# ---------- HELPERS ----------
def sanitize_filename(filename):
    """Remove unsafe characters"""
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    return filename

def timestamped_filename(filename):
    """Prepend ISO timestamp"""
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    return f"{ts}-{sanitize_filename(filename)}"

# ---------- ROUTES ----------
@app.post("/api/v1/upload")
def upload():
    if 'file' not in request.files:
        return jsonify(ok=False, error="No file part"), 400

    f = request.files['file']

    if f.filename == "":
        return jsonify(ok=False, error="No selected file"), 400

    # Validate content type
    if not f.content_type.startswith("image/"):
        return jsonify(ok=False, error="Invalid content type"), 400

    filename = timestamped_filename(f.filename)

    try:
        cc.upload_blob(
            name=filename,
            data=f,
            overwrite=True,
            content_settings=ContentSettings(content_type=f.content_type)
        )
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

    return jsonify(ok=True, url=f"{STORAGE_ACCOUNT_URL}/{IMAGES_CONTAINER}/{filename}")


@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/v1/upload")
def upload_file():   # <-- renamed from `upload`
    f = request.files["file"]
    blob_client = cc.get_blob_client(f.filename)
    blob_client.upload_blob(f, overwrite=True)
    return jsonify(ok=True, url=f"{cc.url}/{f.filename}")

@app.get("/api/v1/gallery")
def gallery():
    urls = [f"{cc.url}/{b.name}" for b in cc.list_blobs()]
    return jsonify(ok=True, gallery=urls)

@app.get("/health")
def health():
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)
