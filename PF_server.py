import csv
import os
import time
import uuid
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
PORTFOLIO_BASE_URL = os.getenv("PORTFOLIO_BASE_URL", "http://127.0.0.1:5000")
LINKEDIN_PROFILE_URL = os.getenv(
    "LINKEDIN_PROFILE_URL",
    "https://www.linkedin.com/in/mohammed-dindrawi",
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

CONVERSATIONS = {}
CONVERSATION_TTL_SECONDS = 60 * 60

PORTFOLIO_PATHS = [
    "/",
    "/about.html",
    "/works.html",
    "/work.html",
    "/contact.html",
]


def clean_text(text):
    return " ".join(text.split())


def scrape_html_page(url, source_name):
    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    status_code = response.status_code
    html = response.text

    if status_code >= 400:
        return {
            "ok": False,
            "source": source_name,
            "url": url,
            "status": f"http_{status_code}",
            "text": "",
            "debug": html[:300],
        }

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else url
    body = clean_text(soup.get_text(" ", strip=True))

    return {
        "ok": True,
        "source": source_name,
        "url": url,
        "status": "loaded",
        "text": f"\n\nSOURCE: {source_name}\nTITLE: {title}\nURL: {url}\nCONTENT:\n{body}",
        "debug": body[:300],
    }


def scrape_portfolio():
    chunks = []
    results = []

    for path in PORTFOLIO_PATHS:
        url = urljoin(PORTFOLIO_BASE_URL, path)
        result = scrape_html_page(url, "portfolio")
        results.append({
            "url": url,
            "status": result["status"],
            "ok": result["ok"],
        })

        if result["ok"]:
            chunks.append(result["text"])

    return {
        "text": "\n".join(chunks)[:12000],
        "results": results,
    }


def scrape_linkedin_public_profile():
    result = scrape_html_page(LINKEDIN_PROFILE_URL, "linkedin")

    if not result["ok"]:
        return result

    text_lower = result["text"].lower()

    blocked_signals = [
        "sign in",
        "join linkedin",
        "authwall",
        "login",
        "challenge",
        "security verification",
        "captcha",
    ]

    profile_signals = [
        "mohammed",
        "dindrawi",
        "edtech",
        "content",
        "education",
        "assessment",
    ]

    blocked = any(signal in text_lower for signal in blocked_signals)
    has_profile_signal = any(signal in text_lower for signal in profile_signals)

    if blocked and not has_profile_signal:
        return {
            "ok": False,
            "source": "linkedin",
            "url": LINKEDIN_PROFILE_URL,
            "status": "blocked_or_login_page",
            "text": "",
            "debug": result["debug"],
        }

    if len(result["text"]) < 500:
        return {
            "ok": False,
            "source": "linkedin",
            "url": LINKEDIN_PROFILE_URL,
            "status": "too_little_content",
            "text": "",
            "debug": result["debug"],
        }

    result["text"] = result["text"][:10000]
    return result


def load_profile_context_fallback():
    profile_path = BASE_DIR / "profile_context.txt"

    if not profile_path.exists():
        return ""

    return profile_path.read_text(encoding="utf-8")[:8000]


def cleanup_old_conversations():
    now = time.time()

    expired_ids = [
        conversation_id
        for conversation_id, data in CONVERSATIONS.items()
        if now - data["created_at"] > CONVERSATION_TTL_SECONDS
    ]

    for conversation_id in expired_ids:
        del CONVERSATIONS[conversation_id]


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


@app.route("/api/load-context", methods=["POST"])
def load_context():
    cleanup_old_conversations()

    portfolio = scrape_portfolio()
    linkedin = scrape_linkedin_public_profile()
    fallback_profile = load_profile_context_fallback()

    context_parts = []

    if linkedin["ok"]:
        context_parts.append(linkedin["text"])
    elif fallback_profile:
        context_parts.append(
            "\n\nSOURCE: linkedin_fallback_cache\n"
            "LinkedIn live scrape did not return usable profile content. "
            "Using local profile_context.txt instead.\n"
            f"{fallback_profile}"
        )

    if portfolio["text"]:
        context_parts.append(portfolio["text"])

    context_text = "\n\n".join(context_parts)[:22000]

    conversation_id = str(uuid.uuid4())

    CONVERSATIONS[conversation_id] = {
        "created_at": time.time(),
        "context": context_text,
        "debug": {
            "linkedin": {
                "ok": linkedin["ok"],
                "status": linkedin["status"],
                "url": linkedin["url"],
                "debug_preview": linkedin["debug"],
            },
            "portfolio": portfolio["results"],
            "context_characters": len(context_text),
            "used_fallback_profile": (not linkedin["ok"] and bool(fallback_profile)),
        },
    }

    return jsonify({
        "ok": True,
        "conversation_id": conversation_id,
        "debug": CONVERSATIONS[conversation_id]["debug"],
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}

    user_message = (data.get("message") or "").strip()
    conversation_id = data.get("conversation_id")
    history = data.get("history") or []

    if not user_message:
        return jsonify({
            "ok": False,
            "error": "Message is required.",
        }), 400

    if not OPENROUTER_API_KEY:
        return jsonify({
            "ok": False,
            "error": "OPENROUTER_API_KEY is missing. Check your .env file.",
        }), 500

    conversation = CONVERSATIONS.get(conversation_id)

    if not conversation:
        return jsonify({
            "ok": False,
            "error": "Conversation context expired or was not loaded. Close and reopen the chat.",
        }), 400

    system_prompt = f"""
You are Mohammed Dindrawi's portfolio assistant.

Use the context below to answer questions about Mohammed Dindrawi.
The context was loaded when the visitor opened the chat.

Rules:
- Use the scraped LinkedIn/profile context and portfolio context.
- Use chat history to understand follow-up questions.
- Do not invent experience, skills, education, projects, employers, or clients.
- If a detail is missing, say you do not have that detail yet.
- Keep answers warm, professional, concise, and useful.
- Encourage the visitor to contact Mohammed for hiring, freelance, or collaboration questions.

STARTUP CONTEXT:
{conversation["context"]}
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    for item in history[-12:]:
        role = item.get("role")
        content = item.get("content")

        if role in ["user", "assistant"] and content:
            messages.append({
                "role": role,
                "content": content[:1200],
            })

    messages.append({
        "role": "user",
        "content": user_message,
    })

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": PORTFOLIO_BASE_URL,
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

    try:
        result = response.json()
    except ValueError:
        return jsonify({
            "ok": False,
            "error": response.text[:500],
        }), response.status_code or 500

    if response.status_code != 200:
        error_message = result.get("error", {}).get("message", str(result))
        return jsonify({
            "ok": False,
            "error": error_message,
        }), response.status_code

    reply = result["choices"][0]["message"]["content"]

    return jsonify({
        "ok": True,
        "reply": reply,
        "debug": conversation["debug"],
    })


@app.route("/debug-assistant")
def debug_assistant():
    return jsonify({
        "api_key_loaded": bool(OPENROUTER_API_KEY),
        "model": OPENROUTER_MODEL,
        "portfolio_base_url": PORTFOLIO_BASE_URL,
        "linkedin_profile_url": LINKEDIN_PROFILE_URL,
        "active_conversations": len(CONVERSATIONS),
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