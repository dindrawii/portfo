# Context: Pick Your Best Model in OpenRouter

## Overview

A new interactive portfolio project/game has been added to the Mohammed Dindrawi portfolio website. It allows visitors to compare two free OpenRouter AI models side by side by submitting a single prompt, viewing both anonymous responses, voting for the preferred answer, and then discovering which model they chose.

This is a mini "Chatbot Arena" style feature, built specifically to showcase AI model comparison capabilities using OpenRouter's free tier.

---

## Feature Summary

- **Game name:** Pick Your Best Model in OpenRouter
- **Route:** `/model-battle`
- **API endpoint:** `POST /api/model-battle`
- **Works page card:** New project card added beside the existing AI Chat card
- **Model pool:** 4 free OpenRouter models (configurable in one location)

---

## The Model Pool

All models are defined in a single constant — `OPENROUTER_FREE_MODELS` — inside `PF_server.py`. This is the only place model IDs appear in the codebase.

```python
OPENROUTER_FREE_MODELS = [
    {
        "id": "qwen/qwen3-coder:free",
        "name": "Qwen3 Coder 480B",
        "category": "coding / agentic tasks",
    },
    {
        "id": "deepseek/deepseek-r1:free",
        "name": "DeepSeek R1 Free",
        "category": "reasoning",
    },
    {
        "id": "openrouter/owl-alpha",
        "name": "OpenRouter Owl Alpha",
        "category": "agentic / long-context",
    },
    {
        "id": "openai/gpt-oss-120b:free",
        "name": "OpenAI GPT-OSS 120B Free",
        "category": "general reasoning / agentic",
    },
]
```

Two models are randomly selected per round. A model is never compared against itself.

---

## API Specification

### `GET /model-battle`
Renders the `model_battle.html` page.

### `POST /api/model-battle`

**Request body:**
```json
{
  "prompt": "user question here",
  "model_a": "optional — override model A ID",
  "model_b": "optional — override model B ID"
}
```

**Validation:**
- `prompt` must not be empty
- `OPENROUTER_API_KEY` must exist in environment
- If model IDs are provided, both must be valid and different

**Success response:**
```json
{
  "ok": true,
  "response_a": "...",
  "response_b": "...",
  "model_a": { "id": "...", "name": "...", "category": "..." },
  "model_b": { "id": "...", "name": "...", "category": "..." }
}
```

**Partial failure response (one model failed):**
```json
{
  "ok": true,
  "response_a": "...",
  "response_b": null,
  "model_a_error": null,
  "model_b_error": "Model returned status 500: ...",
  "model_a": { ... },
  "model_b": { ... }
}
```

**Both models failed:**
```json
{
  "ok": false,
  "error": "Both models failed to respond. Please try again.",
  "details": { "model_a_error": "...", "model_b_error": "..." },
  "model_a": { ... },
  "model_b": { ... }
}
```

**Validation error:**
```json
{
  "ok": false,
  "error": "Prompt is required. Please enter a question or instruction."
}
```

---

## User Flow

1. User visits the Works page and sees the new project card
2. User clicks "Try the Game" → navigates to `/model-battle`
3. User enters a prompt and clicks "Ask two models"
4. Loading spinner appears while both models respond
5. Two anonymous response cards appear (Response A / Response B)
6. User votes: "I prefer A", "Tie", or "I prefer B"
7. Model names and categories are revealed; winner is highlighted
8. Session score updates (stored in `localStorage`)
9. User can start a new round

---

## System Prompt

Both models receive this system message:

> "You are a helpful assistant. Answer clearly and directly."

---

## Security & Design Decisions

- **API key never exposed:** All OpenRouter calls happen server-side in `PF_server.py`. The browser only calls our own backend API.
- **Model pool centralized:** All model IDs live in `OPENROUTER_FREE_MODELS` in `PF_server.py`. No model IDs in frontend code.
- **Same model protection:** The server validates that model A ≠ model B.
- **Graceful degradation:** If one model fails, the user still sees the successful response plus an error message in the failed card.
- **Session score:** Tracked in `localStorage` (key: `model_battle_score`) so it persists across page reloads within the same browser.

---

## Score Object Shape

```json
{
  "qwen/qwen3-coder:free": 2,
  "deepseek/deepseek-r1:free": 1,
  "openrouter/owl-alpha": 0,
  "openai/gpt-oss-120b:free": 3,
  "ties": 1,
  "rounds": 7
}
```

---

## Files Changed/Created

| File | Action | Purpose |
|------|--------|---------|
| `PF_server.py` | Modified | Added model pool, helper functions, `/model-battle` page route, and `/api/model-battle` API endpoint |
| `templates/works.html` | Modified | Added new project card for "Pick Your Best Model" |
| `templates/model_battle.html` | Created | Full game page with HTML structure |
| `static/model-battle.js` | Created | Game logic: submission, loading, rendering, voting, reveal, score tracking |
| `static/model-battle.css` | Created | Styling for responsive card layout, voting UI, score bars, reveal animation |

---

## How to Run & Test

```bash
# 1. Ensure dependencies are installed
pip install -r requirements.txt

# 2. Verify .env has a valid OpenRouter API key
#    OPENROUTER_API_KEY="sk-or-..."

# 3. Run the server
python PF_server.py

# 4. Test locally
#    Works page → http://127.0.0.1:5000/works.html
#    Game page  → http://127.0.0.1:5000/model-battle

# 5. Test the API directly
curl -X POST http://127.0.0.1:5000/api/model-battle \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing in simple terms."}'
```

---

## Relation to Existing Features

- This project is **separate from** the existing AI Chat (`/api/chat`, `ai-chat.html`)
- The existing AI Chat project is completely untouched
- Both projects share the existing `chat.css` for base styling
- The portfolio chatbot widget (injected via `@app.after_request`) is automatically included
- Uses the same OpenRouter API key from `.env`