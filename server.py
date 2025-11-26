import os
from flask import Flask, request
from datetime import datetime

LOG_FILE = r"D:\1C\incoming.log"

# Создаём папку, если её нет
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

app = Flask(__name__)

def log_message(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

@app.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@app.route('/<path:path>', methods=['POST', 'GET'])
def catch_all(path):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Получаем тело запроса
    try:
        body = request.data.decode("utf-8", errors="ignore")
    except:
        body = "<cannot decode>"

    log_entry = [
        "="*60,
        f"Time: {timestamp}",
        f"Path: /{path}",
        f"Method: {request.method}",
        "Headers:",
    ]

    # Заголовки
    for k, v in request.headers.items():
        log_entry.append(f"  {k}: {v}")

    log_entry.append("Body:")
    log_entry.append(body)
    log_entry.append("="*60)

    # Записываем в файл
    log_message("\n".join(log_entry))

    # Можно вернуть любое содержимое, камере всё равно
    return "<ok/>"

# Точка входа для waitress
if __name__ == "__main__":
    from waitress import serve
    print("Starting WSGI server on http://0.0.0.0:80 ...")
    serve(app, host="0.0.0.0", port=80)
