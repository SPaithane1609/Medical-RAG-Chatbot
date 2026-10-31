import os
import traceback
from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
from markupsafe import Markup, escape
from app.config import config  
from app.components.retriever import get_qa_chain

MAX_MESSAGES = 50

app = Flask(__name__)


app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")


app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
Session(app)


def nl2br(value):
    """Escape HTML first (prevents XSS), then convert newlines to <br>."""
    if isinstance(value, dict):
        value = value.get("content", str(value))
    elif not isinstance(value, str):
        value = str(value) if value is not None else ""
    return Markup("<br>\n").join(escape(line) for line in value.split("\n"))


app.jinja_env.filters["nl2br"] = nl2br


@app.route("/", methods=["GET", "POST"])
def index():
    if "messages" not in session:
        session["messages"] = []

    if request.method == "POST":
        user_input = (request.form.get("prompt") or "").strip()

        if user_input:
            messages = session["messages"]
            messages.append({"role": "user", "content": user_input})
            session["messages"] = messages[-MAX_MESSAGES:]

            try:
                qa_chain = get_qa_chain()
                if qa_chain is None:
                    raise Exception("Failed to load QA chain. Check the terminal logs.")

                result = qa_chain.invoke(user_input)

                if isinstance(result, dict):
                    result = result.get("result") or result.get("answer") or str(result)
                else:
                    result = str(result)

                messages.append({"role": "assistant", "content": result})
                session["messages"] = messages[-MAX_MESSAGES:]

            except Exception as e:
                traceback.print_exc()
                error_msg = f"Error: {str(e)}"
                return render_template("index.html", messages=session["messages"], error=error_msg)

        return redirect(url_for("index"))

    return render_template("index.html", messages=session.get("messages", []))


@app.route("/clear")
def clear():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug, use_reloader=False)