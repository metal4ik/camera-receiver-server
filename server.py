import os
import gzip
import base64
from flask import Flask, request
from datetime import datetime
from waitress import serve

# === относительный путь к каталогу "requests" внутри проекта ===
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requests")
os.makedirs(BASE_DIR, exist_ok=True)

LOG_FILE = os.path.join(BASE_DIR, "incoming.log")

app = Flask(__name__)


def log_global(text):
    """Запись в общий лог-файл"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def decode_gzip_if_needed(body: bytes, headers):
    """Раскодировать gzip если Content-Encoding=gzip"""
    if headers.get("Content-Encoding", "").lower() == "gzip":
        try:
            return gzip.decompress(body)
        except Exception as e:
            return body
    return body


def decode_base64_if_needed(text: str):
    """Попытаться раскодировать base64"""
    try:
        decoded = base64.b64decode(text).decode("utf-8", errors="ignore")
        if decoded.strip():
            return decoded
    except Exception:
        pass
    return text


def save_request_file(path, method, headers, body_text):
    """Сохраняем тело запроса в отдельный файл по датам"""

    date_dir = os.path.join(BASE_DIR, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%H-%M-%S_%f")
    safe_path = path.replace("/", "_")

    file_path = os.path.join(date_dir, f"{timestamp}_{method}_{safe_path}.xml")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(body_text)

    return file_path


@app.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@app.route('/<path:path>', methods=['POST', 'GET'])
def catch_all(path):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    raw_body = request.get_data()  # bytes

    # Декодируем GZIP
    raw_body = decode_gzip_if_needed(raw_body, request.headers)

    try:
        body_text = raw_body.decode("utf-8", errors="ignore")
    except:
        body_text = "<cannot decode>"

    # Попытка декодировать base64
    body_text_decoded = decode_base64_if_needed(body_text)

    # Сохранение в отдельный файл
    saved_file = save_request_file(path, request.method, request.headers, body_text_decoded)

    # Запись в общий лог
    log_entry = [
        "=" * 120,
        f"Time: {timestamp}",
        f"Path: /{path}",
        f"Saved file: {saved_file}",
        f"Method: {request.method}",
        "Headers:"
    ]

    for k, v in request.headers.items():
        log_entry.append(f"  {k}: {v}")

    log_entry.append("Body raw:")
    log_entry.append(body_text)
    log_entry.append("Body decoded (base64?):")
    log_entry.append(body_text_decoded)
    log_entry.append("=" * 120)

    log_global("\n".join(log_entry))

    return "<ok/>"


if __name__ == "__main__":
    print("SERVER STARTED: http://0.0.0.0:80")
    serve(app, host="0.0.0.0", port=80)
