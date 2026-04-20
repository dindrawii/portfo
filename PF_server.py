import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, jsonify

app = Flask(__name__)

# =========================
# LOAD ENV VARIABLES
# =========================
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

print("Loaded API Key:", OPENROUTER_API_KEY)  # Debug check


# =========================
# OPENROUTER FUNCTION
# =========================
def ask_openrouter(user_message):
    if not OPENROUTER_API_KEY:
        return {
            "ok": False,
            "error": "OPENROUTER_API_KEY not found in .env",
            "status_code": 500,
        }

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openrouter/free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant on Mohammed Dandrawi's portfolio website. Be clear, friendly, and concise.",
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
            },
            timeout=60,
        )

        print("OpenRouter status:", response.status_code)
        print("OpenRouter response:", response.text)

        data = response.json()

        if response.status_code != 200:
            return {
                "ok": False,
                "error": data.get("error", {}).get("message", "Unknown API error"),
                "status_code": response.status_code,
            }

        return {
            "ok": True,
            "reply": data["choices"][0]["message"]["content"],
            "model": data.get("model", "openrouter/free"),
            "status_code": 200,
        }

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "error": "Request timed out.",
            "status_code": 504,
        }
    except Exception as e:
        print("ERROR in ask_openrouter:", repr(e))
        return {
            "ok": False,
            "error": str(e),
            "status_code": 500,
        }


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/submit_form", methods=["POST", "GET"])
def submit_form():
    if request.method == "POST":
        try:
            data = request.form.to_dict()
            add_to_database(data)
            return redirect("/thankyou.html")
        except Exception as e:
            print("Form error:", e)
            return "Did not save to the database"
    else:
        return "Something went wrong"


# 🔥 AI CHAT ENDPOINT
@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json(silent=True) or {}
        print("Incoming:", data)

        user_message = (data.get("message") or "").strip()

        if not user_message:
            return jsonify({"ok": False, "error": "Message is required."}), 400

        result = ask_openrouter(user_message)

        return jsonify(result), result.get("status_code", 500)

    except Exception as e:
        print("API ERROR:", repr(e))
        return jsonify({"ok": False, "error": str(e)}), 500


# 🔥 IMPORTANT: THIS MUST BE LIKE THIS
@app.route("/<string:page>")
def page(page):
    return render_template(page)


# =========================
# DATABASE
# =========================
def add_to_database(data):
    with open("database.csv", mode="a", newline="", encoding="utf-8") as database:
        email = data["email"]
        subject = data["subject"]
        message = data["message"]

        writer = csv.writer(
            database,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writerow([email, subject, message])


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(debug=True)