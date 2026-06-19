import os

import gradio as gr
import requests
from dotenv import load_dotenv
from supabase import create_client

# The frontend runs on a machine the USER controls, so it only ever gets keys
# that are safe in a browser. SUPABASE_ANON_KEY is the public, publishable key —
# safe precisely because RLS guards every row (db/03_policies.sql). The
# service_role key never comes near this file.
load_dotenv()

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000/diagnose")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_ANON_KEY"],
)


# ---------------------------------------------------------------------------
#  Auth: get the user a passport (JWT) before they can use the app.
#
#  We do NOT build a users table or hash passwords — Supabase Auth does that.
#  We just ask it to sign someone up or log them in, and keep the access_token
#  it hands back. That token is the passport we attach to every backend call.
# ---------------------------------------------------------------------------

def _explain(error: Exception) -> str:
    """Turn a Supabase auth error into one human sentence."""
    message = getattr(error, "message", None) or str(error)
    return f"That did not work: {message}"


def log_in(email, password):
    """Exchange email + password for a session, then reveal the chat."""
    if not email or not password:
        return None, gr.update(), gr.update(), "Enter an email and a password."
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as error:  # wrong password, unknown user, etc.
        return None, gr.update(), gr.update(), _explain(error)

    session = result.session
    if session is None:
        return None, gr.update(), gr.update(), "Could not start a session."
    # Logged in: stash the token, hide the login box, show the chat.
    return (
        session.access_token,
        gr.update(visible=False),
        gr.update(visible=True),
        "",
    )


def sign_up(email, password):
    """Create the account. This project has 'Confirm email' ON, so no session
    is returned yet — the user must click the link in their inbox first, then
    log in. (If you turn confirmation OFF, a session comes straight back and the
    `session is not None` branch below logs them in immediately.)"""
    if not email or not password:
        return None, gr.update(), gr.update(), "Enter an email and a password."
    try:
        result = supabase.auth.sign_up({"email": email, "password": password})
    except Exception as error:  # already registered, weak password, etc.
        return None, gr.update(), gr.update(), _explain(error)

    session = result.session
    if session is None:
        # Email confirmation is on: account made, but no passport until verified.
        return (
            None,
            gr.update(),
            gr.update(),
            "Account created. Check your email to confirm, then log in.",
        )
    return (
        session.access_token,
        gr.update(visible=False),
        gr.update(visible=True),
        "",
    )


# ---------------------------------------------------------------------------
#  The chat, now carrying the passport.
# ---------------------------------------------------------------------------

def diagnose(message, history, token, conversation_id):
    """One chat turn. Carries two things besides the message:

    - the JWT (`token`) — the passport that says who is asking;
    - the `conversation_id` — which thread this belongs to. It is None on the
      first message of a session; the backend then opens a new conversation and
      hands the id back in the `X-Conversation-Id` header. We stash that id and
      send it on every later turn, so follow-ups append to the SAME thread (and
      the model gets the earlier turns as context) instead of starting fresh.

    Returns (reply, conversation_id): the first element is the chat reply, the
    second updates `convo_state` (wired up as an additional output below).
    """
    if not token:
        return "Your session expired. Please reload and log in again.", conversation_id
    body = {"workflow_description": message}
    if conversation_id:
        body["conversation_id"] = conversation_id
    try:
        response = requests.post(
            BACKEND_URL,
            json=body,
            # The passport. The backend hands this straight to Supabase to learn
            # who is asking — it never trusts a name in the request body.
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        response.raise_for_status()
        # Remember the thread the backend put us in (new id on turn one, the same
        # id thereafter), so the next turn continues it.
        new_id = response.headers.get("X-Conversation-Id", conversation_id)
        return response.text, new_id
    except requests.RequestException as e:
        # Keep the existing thread id on error, so a hiccup doesn't fork the thread.
        return f"Could not reach the backend.\n\n{e}", conversation_id


with gr.Blocks(title="Workflow Diagnoser") as demo:
    # Holds the JWT for the length of the browser session.
    token_state = gr.State(None)
    # Holds the current conversation's id. None until the first reply comes back;
    # reset to None on page reload, which is how you start a fresh thread.
    convo_state = gr.State(None)

    # ---- Login view (what you see first) ----
    with gr.Column(visible=True) as login_view:
        gr.Markdown(
            "# Workflow Diagnoser\n"
            "Log in or sign up to start. Your conversations are private to you."
        )
        email = gr.Textbox(label="Email", placeholder="you@example.com")
        password = gr.Textbox(label="Password", type="password")
        with gr.Row():
            login_btn = gr.Button("Log in", variant="primary")
            signup_btn = gr.Button("Sign up")
        status = gr.Markdown()

    # ---- Chat view (hidden until you have a passport) ----
    with gr.Column(visible=False) as chat_view:
        gr.ChatInterface(
            diagnose,
            # Read the passport AND the current thread id...
            additional_inputs=[token_state, convo_state],
            # ...and let diagnose() write the thread id back, so the next turn
            # continues the same conversation.
            additional_outputs=[convo_state],
            title="Workflow Diagnoser",
            description="Describe one repeated task you do at work.",
        )

    outputs = [token_state, login_view, chat_view, status]
    login_btn.click(log_in, [email, password], outputs)
    signup_btn.click(sign_up, [email, password], outputs)


if __name__ == "__main__":
    demo.launch()
