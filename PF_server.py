import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_profile_context():
    profile_path = BASE_DIR / "profile_context.txt"

    if not profile_path.exists():
        return """
Mohammed Dindrawi is an EdTech Content Developer.
He works on educational content, assessment design, Arabic learning materials, and digital learning projects.
"""

    return profile_path.read_text(encoding="utf-8")


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
        except Exception as error:
            return f"Did not save to the database: {error}"

    return "Something went wrong"


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}

    user_message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not user_message:
        return jsonify({
            "ok": False,
            "error": "Message is required."
        }), 400

    if not OPENROUTER_API_KEY:
        return jsonify({
            "ok": False,
            "error": "OPENROUTER_API_KEY is missing. Check your .env file."
        }), 500

    profile_context = load_profile_context()

    system_prompt = f"""
You are Mohammed Dindrawi's portfolio assistant.

Your job:
- Answer visitor questions about Mohammed Dindrawi.
- Use only the profile context below.
- Use chat history to understand follow-up questions.
- Do not invent experience, education, projects, clients, employers, or skills.
- If something is not in the profile context, say you do not have that detail yet.
- Keep answers warm, concise, professional, and suitable for portfolio visitors.
- Encourage visitors to contact Mohammed for hiring, collaboration, or freelance questions.

PROFILE CONTEXT:
{profile_context}
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    for item in history[-12:]:
        role = item.get("role")
        content = item.get("content")

        if role in ["user", "assistant"] and content:
            messages.append({
                "role": role,
                "content": content[:1200]
            })

    messages.append({
        "role": "user",
        "content": user_message
    })

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://dindrawii.pythonanywhere.com",
                "X-Title": "Mohammed Dindrawi Portfolio Assistant",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 500,
            },
            timeout=60,
        )

        result = response.json()

        if response.status_code != 200:
            error_message = result.get("error", {}).get("message", str(result))
            return jsonify({
                "ok": False,
                "error": error_message
            }), response.status_code

        reply = result["choices"][0]["message"]["content"]

        return jsonify({
            "ok": True,
            "reply": reply
        })

    except Exception as error:
        return jsonify({
            "ok": False,
            "error": str(error)
        }), 500


@app.route("/debug-assistant")
def debug_assistant():
    profile_path = BASE_DIR / "profile_context.txt"

    return jsonify({
        "api_key_loaded": bool(OPENROUTER_API_KEY),
        "model": OPENROUTER_MODEL,
        "profile_context_exists": profile_path.exists(),
        "profile_context_characters": len(load_profile_context()),
    })


@app.route("/<path:page>")
def page(page):
    return render_template(page)


def add_to_database(data):
    with open(BASE_DIR / "database.csv", mode="a", newline="", encoding="utf-8") as database:
        email = data.get("email", "")
        subject = data.get("subject", "")
        message = data.get("message", "")

        csv_writer = csv.writer(
            database,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
        )

        csv_writer.writerow([email, subject, message])


if __name__ == "__main__":
    app.run(debug=True)