from flask import Flask, request

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@app.route('/<path:path>', methods=['POST', 'GET'])
def catch_all(path):
    print("=== NEW REQUEST ===")
    print("Path:", path)
    print("Method:", request.method)
    print("Headers:", dict(request.headers))

    try:
        body = request.data.decode("utf-8", errors="ignore")
    except:
        body = "<cannot decode>"

    print("Body:", body)
    print("=== END REQUEST ===\n")

    return "<ok/>"

app.run(host="0.0.0.0", port=80)