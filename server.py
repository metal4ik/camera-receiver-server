from flask import Flask, request

app = Flask(__name__)

@app.route("/", methods=["POST"])
def index():
    print("Headers:", dict(request.headers))
    print("Body:", request.data.decode("utf-8", errors="ignore"))
    return "<ok/>"

app.run(host="0.0.0.0", port=80)
