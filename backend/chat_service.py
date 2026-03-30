"""FemScale AI Coding Tutor — Groq Chat Service (HTTP-based, no SDK)."""

import uuid
import time
import json
import requests
from typing import Optional, Generator

from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, GROQ_TEMPERATURE

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are FemScale AI Tutor — a patient, clear, and encouraging coding mentor.

Your role:
- EXPLAIN code: Break down what code does step-by-step in plain English, then technically.
- DEBUG errors: Analyze error messages, explain WHY they happen, and provide clear fixes.
- TEACH concepts: Explain programming concepts with examples and analogies.

Rules:
1. Be concise but thorough. Use bullet points and numbered steps.
2. Always show corrected code when fixing errors.
3. Use markdown formatting: **bold** for emphasis, `inline code`, and ```python code blocks```.
4. Start explanations with a brief one-line summary, then dive deeper.
5. Be encouraging — never condescending. This is a learning environment.
6. If code is provided, always reference specific line numbers or variables.
7. When explaining errors, use this structure:
   - 🔴 **What went wrong**: Brief description
   - 🔍 **Why it happened**: Technical explanation
   - ✅ **How to fix it**: Step-by-step fix with corrected code
8. Keep responses focused. Don't ramble.
9. If asked about non-coding topics, gently redirect to programming.
10. Use emojis sparingly for visual structure (🔴, 🟢, 💡, ⚡, 📌).
"""

# In-memory session storage
_sessions: dict = {}
MAX_HISTORY_MESSAGES = 40  # Keep last 40 messages (20 exchanges) per session


class ChatSession:
    """Manages a single chat conversation."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = []
        self.created_at = time.time()
        self.title = "New Chat"

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
        # Auto-title from first message
        if len(self.messages) == 1:
            self.title = content[:60].strip()
            if len(content) > 60:
                self.title += "..."
        self._trim()

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        self._trim()

    def _trim(self):
        if len(self.messages) > MAX_HISTORY_MESSAGES:
            self.messages = self.messages[-MAX_HISTORY_MESSAGES:]

    def get_api_messages(self):
        return [{"role": "system", "content": SYSTEM_PROMPT}] + self.messages

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "title": self.title,
            "message_count": len(self.messages),
            "created_at": self.created_at,
        }


def get_or_create_session(session_id: Optional[str] = None) -> ChatSession:
    """Get existing session or create new one."""
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    new_id = session_id or str(uuid.uuid4())
    session = ChatSession(new_id)
    _sessions[new_id] = session
    return session


def list_sessions() -> list:
    """List all chat sessions, newest first."""
    return sorted(
        [s.to_dict() for s in _sessions.values()],
        key=lambda x: x["created_at"],
        reverse=True,
    )


def delete_session(session_id: str) -> bool:
    """Delete a chat session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def _build_full_message(user_message: str, code: str = "") -> str:
    """Build user message with optional code context."""
    if code:
        return f"{user_message}\n\nHere is the code:\n```python\n{code}\n```"
    return user_message


def chat_stream(session_id: str, user_message: str, code: str = "") -> Generator:
    """
    Send message to Groq API and yield response chunks.
    Uses requests library with streaming for SSE output.
    """
    session = get_or_create_session(session_id)
    full_message = _build_full_message(user_message, code)
    session.add_user_message(full_message)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": session.get_api_messages(),
        "max_tokens": GROQ_MAX_TOKENS,
        "temperature": GROQ_TEMPERATURE,
        "stream": True,
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,
        )
        response.raise_for_status()

        full_response = ""
        for line in response.iter_lines():
            if not line:
                continue
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                data_str = line_str[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        full_response += content
                        yield content
                except json.JSONDecodeError:
                    continue

        # Save the complete response to history
        session.add_assistant_message(full_response)

    except requests.exceptions.HTTPError as e:
        error_body = ""
        try:
            error_body = e.response.text
        except Exception:
            pass
        error_msg = f"⚠️ API Error ({e.response.status_code}): {error_body}"
        session.add_assistant_message(error_msg)
        yield error_msg

    except Exception as e:
        error_msg = f"⚠️ Error communicating with AI: {str(e)}"
        session.add_assistant_message(error_msg)
        yield error_msg


def chat_sync(session_id: str, user_message: str, code: str = "") -> str:
    """Non-streaming version — returns full response at once."""
    session = get_or_create_session(session_id)
    full_message = _build_full_message(user_message, code)
    session.add_user_message(full_message)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": session.get_api_messages(),
        "max_tokens": GROQ_MAX_TOKENS,
        "temperature": GROQ_TEMPERATURE,
        "stream": False,
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        session.add_assistant_message(content)
        return content

    except requests.exceptions.HTTPError as e:
        error_body = ""
        try:
            error_body = e.response.text
        except Exception:
            pass
        error_msg = f"⚠️ API Error ({e.response.status_code}): {error_body}"
        session.add_assistant_message(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"⚠️ Error communicating with AI: {str(e)}"
        session.add_assistant_message(error_msg)
        return error_msg
