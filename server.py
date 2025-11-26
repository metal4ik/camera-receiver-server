import os
import re
import base64
from flask import Flask, request
from datetime import datetime
from waitress import serve

# === относительный каталог requests рядом с server.py ===
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requests")
os.makedirs(BASE_DIR, exist_ok=True)

# общий лог
LOG_FILE = os.path.join(BASE_DIR, "incoming.log")

app = Flask(__name__)


def log_global(text):
    """Записывает строку в общий лог-файл"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def extract_and_save_jpeg(body_text, date_dir, timestamp):
    """
    Ищет Base64 JPEG внутри тега <sourceBase64Data ...><![CDATA[...]]></sourceBase64Data>
    и сохраняет JPEG в отдельный файл.
    """

    match = re.search(
        r"<sourceBase64Data[^>]*><!\[CDATA\[(.*?)\]\]></sourceBase64Data>",
        body_text,
        flags=re.S | re.I
    )

    if not match:
        return None

    try:
        b64data = match.group(1).strip()
        b64data = b64data.replace("\n", "").replace("\r", "")

        jpg_bytes = base64.b64decode(b64data)

        jpg_path = os.path.join(date_dir, f"{timestamp}.jpg")
        with open(jpg_path, "wb") as f:
            f.write(jpg_bytes)

        return jpg_path

    except Exception:
        return None


def remove_base64_from_xml(body_text):
    """Полностью удаляет base64 блок из XML."""
    cleaned = re.sub(
        r"<sourceBase64Data[^>]*><!\[CDATA\[(.*?)\]\]></sourceBase64Data>",
        "<sourceBase64Data>[image removed]</sourceBase64Data>",
        body_text,
        flags=re.S | re.I
    )
    return cleaned


@app.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@app.route('/<path:path>', methods=['POST', 'GET'])
def catch_all(path):

    timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    raw_body = request.get_data()  # bytes

    # Пропускаем пустые тела — НЕ сохраняем XML
    if not raw_body or raw_body.strip() == b"":
        log_global(
            "\n".join([
                "=" * 120,
                f"Time: {timestamp_now}",
                f"Path: /{path}",
                f"Method: {request.method}",
                "Body is EMPTY — XML not saved",
                "=" * 120
            ])
        )
        return "<ok/>"

    # Переводим в текст
    try:
        body_text = raw_body.decode("utf-8", errors="ignore")
    except:
        body_text = "<cannot decode UTF-8>"

    # Подготовка каталогов
    date_dir = os.path.join(BASE_DIR, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    short_ts = datetime.now().strftime("%H-%M-%S_%f")

    # JPEG сохраняем отдельно
    jpg_path = extract_and_save_jpeg(body_text, date_dir, short_ts)

    # Base64 убираем
    body_clean = remove_base64_from_xml(body_text)

    # Сохраняем XML
    saved_xml = os.path.join(date_dir, f"{short_ts}_{request.method}_{path.replace('/', '_')}.xml")
    with open(saved_xml, "w", encoding="utf-8") as f:
        f.write(body_clean)

    # Логирование
    log_lines = [
        "=" * 120,
        f"Time: {timestamp_now}",
        f"Path: /{path}",
        f"Method: {request.method}",
        f"Saved XML: {saved_xml}",
    ]

    if jpg_path:
        log_lines.append(f"Saved JPEG: {jpg_path}")

    log_lines.append("Headers:")
    for k, v in request.headers.items():
        log_lines.append(f"  {k}: {v}")

    log_lines.append("Body raw (cleaned):")
    log_lines.append(body_clean)
    log_lines.append("=" * 120)

    log_global("\n".join(log_lines))

    return "<ok/>"


if __name__ == "__main__":
    print("SERVER STARTED: http://0.0.0.0:80")
    serve(app, host="0.0.0.0", port=80)
