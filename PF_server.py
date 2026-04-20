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
            "error": "OPENROUTER_API_KEY was not found in the .env file."
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
        }

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "error": "The AI request timed out. Please try again."
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc)
        }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/submit_form", methods=["POST", "GET"])
def submit_form():
    if request.method == "POST":
        try:
            data = request.form.to_dict()
            addTOdatabase(data)
            return redirect("/thankyou.html")
        except:
            return "Did not save to the DataBase"
    else:
        return "Something went wrong"


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"ok": False, "error": "Message is required."}), 400

    result = ask_openrouter(user_message)
    status_code = 200 if result.get("ok") else result.get("status_code", 500)
    return jsonify(result), status_code


@app.route("/<string:page>")
def page(page):
    return render_template(page)


def addTOdatabase(data):
    with open("database.csv", mode="a", newline="") as database:
        email = data["email"]
        subject = data["subject"]
        message = data["message"]

        csvW = csv.writer(
            database,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL
        )
        csvW.writerow([email, subject, message])