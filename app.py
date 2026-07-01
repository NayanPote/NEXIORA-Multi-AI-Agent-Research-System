import os
import traceback

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from pipeline import run_chat_turn

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
CORS(app)

MAX_HISTORY_MESSAGES = 40  # keep requests bounded


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "nexiora"})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    history = payload.get("history") or []

    if not message:
        return jsonify({"error": "Please enter a message."}), 400

    if len(message) > 4000:
        return jsonify({"error": "Message is too long. Keep it under 4000 characters."}), 400

    if not isinstance(history, list):
        history = []
    history = history[-MAX_HISTORY_MESSAGES:]
    history.append({"role": "user", "content": message})

    try:
        result = run_chat_turn(history)
    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": f"The assistant hit an error: {exc}"}), 500

    return jsonify(
        {
            "reply": result["reply"],
            "history": result["history"],
            "sources": result["sources"],
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
