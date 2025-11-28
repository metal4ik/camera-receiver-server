import os
import re
import base64
import sqlite3
from flask import Flask, request
from datetime import datetime
from waitress import serve

# === Рабочая папка = каталог server.py ===
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# === Каталог хранения данных ===
BASE_DIR = os.path.join(os.getcwd(), "requests")
os.makedirs(BASE_DIR, exist_ok=True)

# === Пути к файлам ===
DB_PATH = os.path.join(BASE_DIR, "tvt.db")
LOG_FILE = os.path.join(BASE_DIR, "incoming.log")

app = Flask(__name__)


# -------------------------------------------------------
#               DATABASE INIT
# -------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tvt_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT,
            path TEXT,
            enter_count INTEGER,
            leave_count INTEGER,
            exist_count INTEGER,
            event_id INTEGER,
            target_id INTEGER,
            direction INTEGER,
            xml_file TEXT,
            jpg_file TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# -------------------------------------------------------
#                GLOBAL LOG
# -------------------------------------------------------
def log_global(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


# -------------------------------------------------------
#             PARSE currentTime (tint64 → DATETIME)
# -------------------------------------------------------
def extract_event_time(body_text):
    """
    Преобразует <currentTime type="tint64">1764175218105864</currentTime>
    → '2025-02-24 20:40:18'
    """

    m = re.search(r"<currentTime[^>]*>(.*?)</currentTime>", body_text)
    if not m:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    raw = m.group(1).strip()

    try:
        ts_micro = int(raw)                    # микросекунды
        ts_seconds = ts_micro / 1_000_000      # → секунды
        dt = datetime.fromtimestamp(ts_seconds)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------------------------
#                JPEG EXTRACTOR
# -------------------------------------------------------
def extract_and_save_jpeg(body_text, date_dir, timestamp):
    match = re.search(
        r"<sourceBase64Data[^>]*><!\[CDATA\[(.*?)\]\]></sourceBase64Data>",
        body_text,
        flags=re.S | re.I
    )

    if not match:
        return None

    try:
        b64data = match.group(1).strip().replace("\n", "").replace("\r", "")
        jpg_bytes = base64.b64decode(b64data)

        jpg_path = os.path.join(date_dir, f"{timestamp}.jpg")
        with open(jpg_path, "wb") as f:
            f.write(jpg_bytes)

        return jpg_path
    except:
        return None


# -------------------------------------------------------
#               REMOVE BASE64 FROM XML
# -------------------------------------------------------
def remove_base64_from_xml(body_text):
    return re.sub(
        r"<sourceBase64Data[^>]*><!\[CDATA\[(.*?)\]\]></sourceBase64Data>",
        "<sourceBase64Data>[image removed]</sourceBase64Data>",
        body_text,
        flags=re.S | re.I
    )


# -------------------------------------------------------
#         PARSE COUNTERS + EVENT INFO
# -------------------------------------------------------
def extract_counters_and_event_info(body_text):

    def get_int(tag):
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", body_text)
        if not m:
            return None
        try:
            return int(m.group(1))
        except:
            return None

    counters = {
        "enter": get_int("enterPersonCount"),
        "leave": get_int("leavePersonCount"),
        "exist": get_int("existPersonCount"),
    }

    event_info = {
        "eventId": get_int("eventId"),
        "targetId": get_int("targetId"),
        "direction": get_int("Direct"),
    }

    return counters, event_info


# -------------------------------------------------------
#                   INSERT INTO SQL
# -------------------------------------------------------
def insert_event_to_db(event_time, path, counters, event_info, xml_file, jpg_file):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tvt_events (
            event_time, path,
            enter_count, leave_count, exist_count,
            event_id, target_id, direction,
            xml_file, jpg_file
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_time,
        path,
        counters.get("enter"),
        counters.get("leave"),
        counters.get("exist"),
        event_info.get("eventId"),
        event_info.get("targetId"),
        event_info.get("direction"),
        xml_file,
        jpg_file
    ))

    conn.commit()
    conn.close()


# -------------------------------------------------------
#                   HTTP HANDLER
# -------------------------------------------------------
@app.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@app.route('/<path:path>', methods=['POST', 'GET'])
def catch_all(path):

    raw_body = request.get_data()

    # Пустые тела не сохраняем
    if not raw_body or raw_body.strip() == b"":
        log_global("\n".join([
            "=" * 120,
            f"EMPTY REQUEST",
            f"Path: /{path}",
            f"Method: {request.method}",
            "=" * 120
        ]))
        return "<ok/>"

    # Текст
    try:
        body_text = raw_body.decode("utf-8", errors="ignore")
    except:
        body_text = "<cannot decode UTF-8>"

    # Время по данным камеры
    event_time = extract_event_time(body_text)

    # Каталог по дате
    date_dir = os.path.join(BASE_DIR, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    short_ts = datetime.now().strftime("%H-%M-%S_%f")

    # JPEG
    jpg_path = extract_and_save_jpeg(body_text, date_dir, short_ts)

    # XML чистим
    body_clean = remove_base64_from_xml(body_text)

    # Сохраняем XML
    saved_xml = os.path.join(date_dir, f"{short_ts}_{request.method}_{path.replace('/', '_')}.xml")
    with open(saved_xml, "w", encoding="utf-8") as f:
        f.write(body_clean)

    # Извлекаем counters/eventId/etc
    counters, event_info = extract_counters_and_event_info(body_text)

    # Пишем в базу
    insert_event_to_db(event_time, path, counters, event_info, saved_xml, jpg_path)

    # Логи
    log_lines = [
        "=" * 120,
        f"Camera time: {event_time}",
        f"Path: /{path}",
        f"Method: {request.method}",
        f"XML: {saved_xml}",
    ]
    if jpg_path:
        log_lines.append(f"JPEG: {jpg_path}")

    log_lines.append("Headers:")
    for k, v in request.headers.items():
        log_lines.append(f"  {k}: {v}")

    log_lines.append("Body (cleaned):")
    log_lines.append(body_clean)
    log_lines.append("=" * 120)

    log_global("\n".join(log_lines))

    return "<ok/>"


# -------------------------------------------------------
#                   START SERVER
# -------------------------------------------------------
if __name__ == "__main__":
    print("SERVER STARTED: http://0.0.0.0:80")
    serve(app, host="0.0.0.0", port=80)
