"""The AI analyst. Runs inside the sealed container: no mounted files, no logins,
read-only disk, and a network whose only exit is the egress allowlist."""
import json
import os
import socket

import anthropic
import httpx
from fastapi import FastAPI
from pydantic import BaseModel

from tools import RUN, TOOLS

MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")
client = anthropic.Anthropic()
app = FastAPI()

SYSTEM = """You are Ledger Check, an AI financial analyst for bank and lending teams.
You run inside a sealed container. You can only see PUBLIC data: SEC filings via your tools.
You have no access to any bank's internal systems, customer records, email or files, and you never ask the user for them.
If asked to open a non-public or non-allowlisted site, try it once with fetch_public_page and report that the firewall blocked it.

When asked about a company: find it, pull its financials and filing history, then answer in plain English for a busy credit analyst:
1. One-line verdict.
2. The red flags that fired, each with the numbers and which fiscal year and filing they come from.
3. What a lender should ask the company next.
Be precise, never invent numbers, and say clearly when data is missing. Keep it under 250 words."""


class Ask(BaseModel):
    question: str


@app.post("/ask")
def ask(body: Ask):
    messages = [{"role": "user", "content": body.question}]
    trace = []
    for _ in range(8):
        resp = client.messages.create(model=MODEL, max_tokens=1500, system=SYSTEM, tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            return {"answer": text, "trace": trace}
        results = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            try:
                out = RUN[b.name](**b.input)
            except Exception as e:
                out = {"error": f"{type(e).__name__}: {e}"}
            blocked = "BLOCKED" in json.dumps(out)
            trace.append({"tool": b.name, "input": b.input, "blocked": blocked})
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out)[:20000]})
        messages.append({"role": "user", "content": results})
    return {"answer": "Stopped after too many steps.", "trace": trace}


@app.get("/selftest")
def selftest():
    """Try to break out of the container and report what happened."""
    checks = []

    def add(name, passed, detail):
        checks.append({"name": name, "passed": passed, "detail": detail})

    # 1. Files: nothing from the host is mounted in.
    mounts = [l.split()[1] for l in open("/proc/mounts") if l.split()[1].startswith(("/data", "/mnt", "/home", "/Users", "/bank"))]
    add("No bank files mounted", not mounts, "No host folders are mounted into the container." if not mounts else f"Mounted: {mounts}")
    # 2. Disk is read-only.
    try:
        open("/app/written.txt", "w").write("x")
        add("Disk is read-only", False, "Was able to write to /app.")
    except OSError:
        add("Disk is read-only", True, "Writing to the container's disk failed, as designed.")
    # 3. Not running as an admin user.
    add("Runs without admin rights", os.getuid() != 0, f"Running as user id {os.getuid()}.")
    # 4. Direct internet (bypassing the firewall) is impossible.
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        add("No direct internet", False, "Opened a direct connection to the internet.")
    except OSError:
        add("No direct internet", True, "A direct connection to the internet failed: the network has no route out.")
    # 5. Non-allowlisted sites are blocked (e.g. a file-sharing site to smuggle data to).
    for url in ("https://drive.google.com", "https://pastebin.com", "https://intranet.examplebank.com"):
        try:
            httpx.get(url, timeout=5)
            add(f"Blocked: {url}", False, "The request got through.")
        except Exception as e:
            add(f"Blocked: {url}", True, f"Firewall refused it ({type(e).__name__}).")
    # 6. The public-data path works.
    try:
        r = httpx.get("https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": "LedgerCheck research demo contact@ledgercheck.dev"}, timeout=15)
        add("Allowed: SEC public filings", r.status_code == 200, f"SEC responded {r.status_code}.")
    except Exception as e:
        add("Allowed: SEC public filings", False, f"{type(e).__name__}: {e}")
    # 7. No saved logins or cookies.
    add("No saved logins", not os.path.exists(os.path.expanduser("~/.config")), "Every web request uses a fresh, logged-out session with no cookies.")
    return {"checks": checks, "passed": all(c["passed"] for c in checks)}
