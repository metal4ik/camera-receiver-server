import os
import re
import gzip
import base64
from flask import Flask, request
from datetime import datetime
from waitress import serve

# === относительный каталог requests рядом с server.py ===
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requests")
os.makedirs(BASE_DIR, exist_ok=True)

LOG_FILE = os.path.join(BASE_DIR, "incoming.log")

app = Flask(__name__)

# Base64 валидация
BASE64_REGEX = re.compile(r'^[A-Za-z0-9+/=\r\n]+$')


def log_global(text):
    """Записывает строку в общий лог-файл"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def decode_gzip_if_needed(body: bytes, headers):
    """Декодировать gzip если нужно"""
    if headers.get("Content-Encoding", "").lower() == "gzip":
        try:
            return gzip.decompress(body)
        except Exception:
            return body
    return body


def extract_and_save_jpeg(body_text, date_dir, timestamp):
    """
    Ищет <sourceBase64Data><![CDATA[...]]></...> и сохраняет JPEG.
    """
    match = re.search(
        r"<sourceBase64Data><!\[CDATA\[(.*?)\]\]></sourceBase64Data>",
        body_text,
        flags=re.S
    )

    if not match:
        return None

    try:
        b64data = match.group(1).replace("\n", "")
        jpg_bytes = base64.b64decode(b64data)

        jpg_path = os.path.join(date_dir, f"{timestamp}.jpg")
        with open(jpg_path, "wb") as f:
            f.write(jpg_bytes)

        return jpg_path

    except Exception:
        return None


def save_request_file(path, method, body_text):
    """
    Сохраняет тело запроса в XML файл в каталоге по дате.
    """
    date_dir = os.path.join(BASE_DIR, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%H-%M-%S_%f")
    safe_path = path.replace("/", "_")

    file_path = os.path.join(date_dir, f"{timestamp}_{method}_{safe_path}.xml")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(body_text)

    return file_path, date_dir, timestamp


@app.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@app.route('/<path:path>', methods=['POST', 'GET'])
def catch_all(path):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    raw_body = request.get_data()  # bytes

    # GZIP decode
    raw_body = decode_gzip_if_needed(raw_body, request.headers)

    # raw → текст UTF-8
    try:
        body_text = raw_body.decode("utf-8", errors="ignore")
    except:
        body_text = "<cannot decode UTF-8>"

    # сохраняем XML
    saved_file, date_dir, ts_short = save_request_file(path, request.method, body_text)

    # извлекаем JPEG, если есть
    jpg_path = extract_and_save_jpeg(body_text, date_dir, ts_short)

    # составление глобального лога
    log_entry = [
        "=" * 120,
        f"Time: {timestamp}",
        f"Path: /{path}",
        f"Method: {request.method}",
        f"Saved XML: {saved_file}",
    ]

    if jpg_path:
        log_entry.append(f"Saved JPEG: {jpg_path}")

    log_entry.append("Headers:")
    for k, v in request.headers.items():
        log_entry.append(f"  {k}: {v}")

    log_entry.append("Body raw:")
    log_entry.append(body_text)
    log_entry.append("=" * 120)

    log_global("\n".join(log_entry))

    return "<ok/>"


if __name__ == "__main__":
    print("SERVER STARTED: http://0.0.0.0:80")
    serve(app, host="0.0.0.0", port=80)
