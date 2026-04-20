import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, jsonify

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def ask_openrouter(user_message):
    if not OPENROUTER_API_KEY:
        return {
            "ok": False,
            "error": "OPENROUTER_API_KEY was not found in the .env file.",
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
                        "content": (
                            "You are a helpful assistant on Mohammed Dandrawi's portfolio website. "
                            "Be clear, friendly, and concise."
                        ),
                    },
                    {
                        "role": "user",
                        "content": user_message,
                    },
                ],
            },
            timeout=60,
        )

        raw_text = response.text
        try:
            data = response.json()
        except ValueError:
            return {
                "ok": False,
                "error": f"Non-JSON response from OpenRouter: {raw_text[:300]}",
                "status_code": response.status_code or 500,
            }

        if response.status_code != 200:
            return {
                "ok": False,
                "error": data.get("error", {}).get("message", "Unknown API error"),
                "status_code": response.status_code,
            }

        choices = data.get("choices", [])
        if not choices:
            return {
                "ok": False,
                "error": "No choices were returned by OpenRouter.",
                "status_code": 502,
            }

        message = choices[0].get("message", {})
        reply = message.get("content")

        if not reply:
            return {
                "ok": False,
                "error": "OpenRouter returned an empty message.",
                "status_code": 502,
            }

        return {
            "ok": True,
            "reply": reply,
            "model": data.get("model", "openrouter/free"),
            "status_code": 200,
        }

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "error": "The AI request timed out. Please try again.",
            "status_code": 504,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "status_code": 500,
        }


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
        except Exception as exc:
            return f"Did not save to the database: {exc}"
    else:
        return "Something went wrong"


@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()

        if not user_message:
            return jsonify({"ok": False, "error": "Message is required."}), 400

        result = ask_openrouter(user_message)
        return jsonify(result), result.get("status_code", 500)

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/<string:page>")
def page(page):
    return render_template(page)


def add_to_database(data):
    with open("database.csv", mode="a", newline="", encoding="utf-8") as database:
        email = data["email"]
        subject = data["subject"]
        message = data["message"]

        csv_writer = csv.writer(
            database,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
        )
        csv_writer.writerow([email, subject, message])


if __name__ == "__main__":
    app.run(debug=True)