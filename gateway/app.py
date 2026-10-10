"""Gateway: the only door into the sealed analyst. Serves the app, runs the data guard,
keeps the audit log."""
import mimetypes
import os
import time
from collections import deque

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from guard import redact, scan

SANDBOX = os.environ.get("SANDBOX_URL", "http://sandbox:9000")
EGRESS_LOG = os.environ.get("EGRESS_LOG", "http://egress:8889/log")
AUDIT = deque(maxlen=300)
mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("text/javascript", ".mjs")
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/shield", StaticFiles(directory="static/shield", html=True), name="shield")


def audit(kind, summary, **extra):
    AUDIT.append({"t": time.time(), "kind": kind, "summary": summary, **extra})


class Ask(BaseModel):
    question: str


@app.get("/")
def index():
    return RedirectResponse("/shield/")


@app.get("/analyst")
def analyst():
    return FileResponse("static/index.html")


@app.post("/api/ask")
def ask(body: Ask):
    q = body.question.strip()[:4000]
    hits = scan(q)
    if hits:
        audit("blocked", "Question blocked before reaching the AI", rules=[h["rule"] for h in hits])
        return {"blocked": True, "hits": hits}
    audit("allowed", "Question passed the data guard", chars=len(q))
    try:
        r = httpx.post(f"{SANDBOX}/ask", json={"question": q}, timeout=180)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        audit("error", f"Analyst error: {type(e).__name__}")
        return {"blocked": False, "answer": f"The analyst hit an error ({type(e).__name__}). Try again.", "trace": []}
    answer = redact(data.get("answer", ""))
    for t in data.get("trace", []):
        audit("tool-blocked" if t["blocked"] else "tool", f"{t['tool']} {t['input']}")
    return {"blocked": False, "answer": answer, "trace": data.get("trace", [])}


@app.get("/api/selftest")
def selftest():
    r = httpx.get(f"{SANDBOX}/selftest", timeout=60)
    res = r.json()
    audit("selftest", f"Isolation test: {sum(c['passed'] for c in res['checks'])}/{len(res['checks'])} passed")
    return res


@app.get("/api/audit")
def get_audit():
    try:
        eg = httpx.get(EGRESS_LOG, timeout=3).json()
    except Exception:
        eg = {"allowlist": [], "events": []}
    return {"gateway": list(AUDIT)[::-1][:60], "egress": eg["events"][::-1][:60], "allowlist": eg["allowlist"]}
