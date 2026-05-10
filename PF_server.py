import csv
import os
import random
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for

# --------------------------------------------------
# App setup
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

app = Flask(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# --------------------------------------------------
# Model pool for the "Pick Your Best Model" game
# --------------------------------------------------
OPENROUTER_FREE_MODELS = [
    {
        "id": "qwen/qwen3-coder:free",
        "name": "Qwen3 Coder 480B",
        "category": "coding / agentic tasks",
    },
    {
        "id": "inclusionai/ring-2.6-1t:free",
        "name": "InclusionAI R2.6-1T",
        "category": "reasoning",
    },
    {
        "id": "openai/gpt-oss-20b:free",
        "name": "OpenAI GPT-OSS 20B",
        "category": "agentic / long-context",
    },
    {
        "id": "openai/gpt-oss-120b:free",
        "name": "OpenAI GPT-OSS 120B Free",
        "category": "general reasoning / agentic",
    },
]


def pick_two_models():
    """Randomly select two different models from the pool."""
    if len(OPENROUTER_FREE_MODELS) < 2:
        raise ValueError("Model pool must contain at least two models.")
    pair = random.sample(OPENROUTER_FREE_MODELS, 2)
    return pair[0], pair[1]


def validate_model_id(model_id):
    """Check that a model ID exists in the pool."""
    return any(m["id"] == model_id for m in OPENROUTER_FREE_MODELS)


# --------------------------------------------------
# Automatically add chatbot files to every HTML page
# --------------------------------------------------

@app.after_request
def inject_chatbot_assets(response):
    content_type = response.headers.get("Content-Type", "")

    if "text/html" not in content_type:
        return response

    html = response.get_data(as_text=True)

    if "ai-chat.js" in html:
        return response

    chatbot_assets = f"""
<link rel="stylesheet" href="{url_for('static', filename='chat.css')}">
<script src="{url_for('static', filename='ai-chat.js')}"></script>
"""

    if "</body>" in html:
        html = html.replace("</body>", chatbot_assets + "\n</body>")
    else:
        html += chatbot_assets

    response.set_data(html)
    response.headers["Content-Length"] = str(len(response.get_data()))

    return response


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def load_profile_context():
    profile_path = BASE_DIR / "profile_context.txt"

    if not profile_path.exists():
        return """
Mohammed Dindrawi is an EdTech Content Developer.
He works on educational content, assessment design, Arabic learning materials, and digital learning projects.
"""

    return profile_path.read_text(encoding="utf-8")


def add_to_database(data):
    database_path = BASE_DIR / "database.csv"

    with open(database_path, mode="a", newline="", encoding="utf-8") as database:
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


# --------------------------------------------------
# Website routes
# --------------------------------------------------

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


@app.route("/<path:page>")
def render_page(page):
    return render_template(page)


# --------------------------------------------------
# Model Battle page route
# --------------------------------------------------

@app.route("/model-battle")
def model_battle():
    return render_template("model_battle.html", openrouter_free_models=OPENROUTER_FREE_MODELS)


# --------------------------------------------------
# Model Battle API
# --------------------------------------------------

SYSTEM_PROMPT = "You are a helpful assistant. Answer clearly and directly."


@app.route("/api/model-battle", methods=["POST"])
def api_model_battle():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()

    # Allow caller to optionally pass specific model IDs; otherwise pick randomly.
    model_a_id = (data.get("model_a") or "").strip() or None
    model_b_id = (data.get("model_b") or "").strip() or None

    # Validate API key
    if not OPENROUTER_API_KEY:
        return jsonify({
            "ok": False,
            "error": "OPENROUTER_API_KEY is not configured on the server."
        }), 500

    # Validate prompt
    if not prompt:
        return jsonify({
            "ok": False,
            "error": "Prompt is required. Please enter a question or instruction."
        }), 400

    # Resolve model pair
    if model_a_id and model_b_id:
        if model_a_id == model_b_id:
            return jsonify({
                "ok": False,
                "error": "The two models must be different."
            }), 400
        if not validate_model_id(model_a_id):
            return jsonify({
                "ok": False,
                "error": f"Unknown model A: {model_a_id}"
            }), 400
        if not validate_model_id(model_b_id):
            return jsonify({
                "ok": False,
                "error": f"Unknown model B: {model_b_id}"
            }), 400
        model_a = next(m for m in OPENROUTER_FREE_MODELS if m["id"] == model_a_id)
        model_b = next(m for m in OPENROUTER_FREE_MODELS if m["id"] == model_b_id)
    else:
        model_a, model_b = pick_two_models()

    # Call both models
    def call_model(model_info):
        try:
            resp = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://dindrawii.pythonanywhere.com",
                    "X-Title": "Pick Your Best Model - Mohammed Portfolio",
                },
                json={
                    "model": model_info["id"],
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
                timeout=60,
            )
            if resp.status_code != 200:
                error_detail = ""
                try:
                    err_json = resp.json()
                    error_detail = err_json.get("error", {}).get("message", resp.text[:300])
                except Exception:
                    error_detail = resp.text[:300]
                return {
                    "ok": False,
                    "error": f"Model {model_info['name']} returned status {resp.status_code}: {error_detail}",
                }
            result = resp.json()
            reply = result["choices"][0]["message"]["content"]
            return {"ok": True, "reply": reply}
        except requests.exceptions.Timeout:
            return {"ok": False, "error": "Request timed out."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    result_a = call_model(model_a)
    result_b = call_model(model_b)

    # Build response
    response_payload = {
        "model_a": model_a,
        "model_b": model_b,
    }

    if not result_a["ok"] and not result_b["ok"]:
        return jsonify({
            "ok": False,
            "error": "Both models failed to respond. Please try again.",
            "details": {
                "model_a_error": result_a["error"],
                "model_b_error": result_b["error"],
            },
            **response_payload,
        }), 502

    response_payload["response_a"] = result_a.get("reply") or None
    response_payload["response_b"] = result_b.get("reply") or None
    response_payload["model_a_error"] = result_a.get("error") if not result_a["ok"] else None
    response_payload["model_b_error"] = result_b.get("error") if not result_b["ok"] else None
    response_payload["ok"] = True

    return jsonify(response_payload)


# --------------------------------------------------
# Chatbot route
# --------------------------------------------------

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
            "error": "OPENROUTER_API_KEY is missing. Check your .env file on PythonAnywhere."
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
                "status_code": response.status_code,
            }), response.status_code

        reply = result["choices"][0]["message"]["content"]

        return jsonify({
            "ok": True,
            "reply": reply,
            "model": result.get("model", OPENROUTER_MODEL),
        })

    except requests.exceptions.Timeout:
        return jsonify({
            "ok": False,
            "error": "The AI request timed out. Please try again."
        }), 504

    except Exception as error:
        return jsonify({
            "ok": False,
            "error": str(error)
        }), 500


# --------------------------------------------------
# Temporary debug route
# --------------------------------------------------

@app.route("/debug-assistant")
def debug_assistant():
    profile_path = BASE_DIR / "profile_context.txt"
    env_path = BASE_DIR / ".env"

    return jsonify({
        "base_dir": str(BASE_DIR),
        "env_path": str(env_path),
        "env_file_exists": env_path.exists(),
        "api_key_loaded": bool(OPENROUTER_API_KEY),
        "api_key_preview": OPENROUTER_API_KEY[:12] if OPENROUTER_API_KEY else None,
        "model": OPENROUTER_MODEL,
        "profile_context_exists": profile_path.exists(),
        "profile_context_characters": len(load_profile_context()),
        "chat_injection_enabled": True,
    })


# --------------------------------------------------
# Local development only
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
