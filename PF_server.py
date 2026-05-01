import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://your-portfolio-url.com",
        "X-Title": "Mohammed Dindrawi Portfolio Assistant",
    },
)


def load_profile_context():
    context_path = Path("profile_context.txt")

    if not context_path.exists():
        return (
            "Mohammed Dindrawi is an EdTech Content Developer. "
            "He transforms curricula into structured digital assessments."
        )

    return context_path.read_text(encoding="utf-8")


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
            print(error)
            return "Did not save to the database"

    return "Something went wrong"


@app.route("/api/chat", methods=["POST"])
def chat():
    if not OPENROUTER_API_KEY:
        return jsonify({
            "ok": False,
            "error": "OPENROUTER_API_KEY was not found on the server."
        }), 500

    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({
            "ok": False,
            "error": "Please write a message first."
        }), 400

    profile_context = load_profile_context()

    system_prompt = f"""
You are Mohammed Dindrawi's portfolio assistant.

Your job:
- Answer questions about Mohammed Dindrawi professionally.
- Use only the profile information provided below.
- If the visitor asks about something not in the profile, say that you do not have that detail yet.
- Keep answers concise, warm, and suitable for portfolio visitors.
- Encourage users to contact Mohammed for work, collaboration, or hiring questions.

Profile information:
{profile_context}
"""

    try:
        completion = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=400,
        )

        reply = completion.choices[0].message.content

        return jsonify({
            "ok": True,
            "reply": reply,
            "model": OPENROUTER_MODEL,
        })

    except Exception as error:
        print(error)
        return jsonify({
            "ok": False,
            "error": "The assistant could not answer right now."
        }), 500


@app.route("/<path:page>")
def render_page(page):
    return render_template(page)


def add_to_database(data):
    with open("database.csv", mode="a", newline="", encoding="utf-8") as database:
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