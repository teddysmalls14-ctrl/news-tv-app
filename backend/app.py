import os
import subprocess
import uuid
from flask import Flask, request, jsonbify
from flask_cors import CORS
import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
WATERMARK_TEXT = os.getenv("WATERMARK_TEXT", "BC News Ent TV")

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version="s3v4"),
)


@app.route("/api/upload-video", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonbify({"error": "No se recibio video"}), 400

    file = request.files["video"]
    filename = f"{uuid.uuid4()}_{file.filename}"
    input_path = f"/tmp/{filename}"
    output_path = f"/tmp/wm_{filename}"

    file.save(input_path)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"drawtext=text='{WATERMARK_TEXT}':fontsize=24:fontcolor=white@0.7:x=10:y=10",
        "-c:a", "copy", "-preset", "fast", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return jsonbify({"error": "FFmpeg fallo", "detail": result.stderr}), 500

    key = f"videos/{filename}"
    s3.upload_file(output_path, R2_BUCKET, key, ExtraArgs={"ContentType": "video/mp4"})

    os.remove(input_path)
    os.remove(output_path)

    public_url = f"{R2_ENDPOINT}/{R2_BUCKET}/{key}"
    return jsonbify({"url": public_url, "key": key}), 200


@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    if "image" not in request.files:
        return jsonbify({"error": "No se recibio imagen"}), 400

    file = request.files["image"]
    filename = f"{uuid.uuid4()}_{file.filename}"
    key = f"images/{filename}"
    s3.upload_fileobj(file, R2_BUCKET, key, ExtraArgs={"ContentType": file.content_type})

    public_url = f"{R2_ENDPOINT}/{R2_BUCKET}/{key}"
    return jsonbify({"url": public_url, "key": key}), 200


@app.route("/api/health", methods=["GET"])
def health():
    return jsonbify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=5000, debug=True)