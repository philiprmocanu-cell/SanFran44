"""Deal Desk: ask senior bankers about a deal, anonymously.

Askers and seniors only ever see each other's anonymous handle and level.
Client names inside a deal are swapped for the deal's codename before a senior sees them.
Replies are turned into a Sense-style result (answer, quotes, reasons, watch-outs) by Claude.
"""
import json
import os
import random
import re
import time
import uuid

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/desk")
KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("DESK_MODEL", "claude-sonnet-5-5")

# ---------- Deal database (fictional deals, modelled on real deal patterns) ----------
DEALS = [
    dict(id="falcon", code="Project Falcon", type="Acquisition", sector="Healthcare", value=3.4, status="Signed, closing Q1",
         parties=["Northwind Health", "Cedar Lane Diagnostics"],
         headline="Northwind Health to acquire Cedar Lane Diagnostics for $3.4B cash",
         facts=["$41.50 per share, 32% premium to unaffected price", "$180M run-rate cost synergies by year 3",
                "Funded with $2.2B new term loan B + cash on hand", "HSR filed; second request risk on 4 regional labs"]),
    dict(id="harbor", code="Project Harbor", type="Merger", sector="Banking", value=6.1, status="Pending regulatory",
         parties=["Bayview Bancorp", "Summit Valley Financial"],
         headline="Bayview Bancorp and Summit Valley Financial merger of equals ($6.1B all-stock)",
         facts=["0.84 exchange ratio, 52/48 pro forma ownership", "Combined $78B assets crosses $50B supervision tier",
                "Core systems conversion planned 9 months post close", "Expected branch overlap: 61 of 410 branches"]),
    dict(id="ironwood", code="Project Ironwood", type="LBO", sector="Industrials", value=1.9, status="Financing committed",
         parties=["Kestrel Capital", "Atlas Freight Systems"],
         headline="Kestrel Capital LBO of Atlas Freight Systems at 9.1x EBITDA",
         facts=["$1.9B enterprise value, 45% equity cheque", "Total leverage 5.3x, first-lien 4.0x",
                "Covenant-lite TLB, 6-month 101 soft call", "Management rollover 8%"]),
    dict(id="lumen", code="Project Lumen", type="Spin-off", sector="Technology", value=2.7, status="Form 10 filed",
         parties=["Helio Semiconductor", "Lumen Power"],
         headline="Helio Semiconductor spins off its power-chip unit as Lumen Power",
         facts=["Tax-free spin under Section 355", "$900M one-time dividend to parent funded by new notes",
                "Transition services agreement for 18 months", "Index inclusion expected at listing"]),
    dict(id="orchard", code="Project Orchard", type="Divestiture", sector="Consumer", value=0.85, status="Auction round 2",
         parties=["Greenfield Foods", "Pantry Brands"],
         headline="Greenfield Foods sells snacks unit; Pantry Brands lead bidder at $850M",
         facts=["Carve-out financials, 3 years audited", "Two strategic + three sponsor bids in round 2",
                "Shared co-packing plant needs a supply agreement", "Stranded costs est. $22M"]),
    dict(id="tidewater", code="Project Tidewater", type="Acquisition", sector="Energy", value=4.2, status="Announced",
         parties=["Meridian Energy", "Norvik Offshore"],
         headline="Meridian Energy acquires Norvik Offshore's wind portfolio for $4.2B",
         facts=["2.1 GW operating capacity, 1.3 GW in construction", "Tax-equity partnerships transfer with the assets",
                "Contracted revenue 87% for 12 years", "CFIUS review not required"]),
    dict(id="quill", code="Project Quill", type="Take-private", sector="Technology", value=5.5, status="Go-shop period",
         parties=["Ridgeline Partners", "Vantage Software"],
         headline="Ridgeline Partners to take Vantage Software private for $5.5B",
         facts=["30-day go-shop, 2.1% break fee in go-shop / 3.5% after", "Recurring revenue 92%, rule of 40 = 38",
                "Private credit unitranche $2.4B", "Founder voting agreement covers 19%"]),
    dict(id="sterling", code="Project Sterling", type="Hostile bid", sector="Insurance", value=7.8, status="Tender offer open",
         parties=["Crestmark Insurance", "Pinnacle Re"],
         headline="Crestmark Insurance launches $7.8B hostile tender for Pinnacle Re",
         facts=["$66 per share cash, 41% premium", "Target board adopted a 10% poison pill",
                "Proxy fight for 4 board seats at annual meeting", "Rating agencies placed both on watch"]),
    dict(id="atlas", code="Project Atlas", type="Merger", sector="Media", value=12.0, status="DOJ second request",
         parties=["Apex Media", "Signal Studios"],
         headline="Apex Media and Signal Studios $12B merger hit by DOJ second request",
         facts=["$1.1B reverse termination fee payable to Signal", "Outside date 18 months, two 3-month extensions",
                "Possible remedy: divest sports networks", "Combined streaming share ~19%"]),
    dict(id="beacon", code="Project Beacon", type="Company event", sector="Retail", value=0.0, status="Earnings next week",
         parties=["Corvid Retail"],
         headline="Corvid Retail: Q3 earnings, guidance cut expected, covenant headroom tight",
         facts=["Revolver springing covenant at 4.5x; LTM 4.2x", "Same-store sales -6% guided",
                "Activist holds 7.4% and wants a sale process", "Banks asked for an amend-and-extend"]),
]
DEAL_BY_ID = {d["id"]: d for d in DEALS}

FILE_KINDS = [
    ("Term sheet summary", "pdf"), ("Synergy & model notes", "xlsx"), ("Regulatory timeline", "docx"),
    ("Committee memo", "pdf"),
]


def deal_files(d):
    out = []
    for i, (name, ext) in enumerate(FILE_KINDS[: 3 if d["type"] != "Company event" else 2]):
        body = [f"{name.upper()} — {d['headline']}", f"Status: {d['status']}", ""]
        body += [f"• {f}" for f in d["facts"]]
        if i == 1:
            body += ["", "Key sensitivities: synergy phasing (±1 yr), exit multiple (±1.0x), rate +100bp."]
        if i == 2:
            body += ["", "Milestones: signing → filings (wk 2) → waiting period (30d) → close conditions → close."]
        out.append(dict(id=f"{d['id']}-{i}", name=f"{d['code']} – {name}.{ext}", text="\n".join(body)))
    return out


def scrub(text, deal):
    """Swap the deal's client names for its codename before a senior sees it."""
    if not deal or not text:
        return text
    for j, p in enumerate(deal["parties"]):
        tag = deal["code"] + (" (Buyer)" if j == 0 and len(deal["parties"]) > 1 else " (Target)" if j == 1 else "")
        names = [p] + ([p.rsplit(" ", 1)[0]] if p.count(" ") >= 2 else []) + [p.split()[0]]
        for n in names:
            text = re.sub(r"\b" + re.escape(n) + r"\b(?![^()]*\))", tag, text, flags=re.I)
    return text


def public_deal(d, scrubbed=False):
    x = dict(d)
    x["files"] = deal_files(d)
    if scrubbed:
        x["headline"] = scrub(d["headline"], d)
        x["parties"] = []
        for f in x["files"]:
            f["text"] = scrub(f["text"], d)
            f["name"] = f["name"]
    return x


# ---------- People (anonymous handles only) ----------
SENIORS = [
    dict(id="s1", title="Managing Director", desk="M&A · Healthcare & Consumer", years=22, tags=["Healthcare", "Consumer", "Acquisition", "Divestiture"]),
    dict(id="s2", title="Managing Director", desk="Leveraged Finance", years=18, tags=["LBO", "Take-private", "Company event", "Industrials"]),
    dict(id="s3", title="Director", desk="Regulatory & Antitrust", years=15, tags=["Merger", "Banking", "Media", "Hostile bid"]),
    dict(id="s4", title="Senior Executive", desk="Post-merger Integration", years=20, tags=["Merger", "Spin-off", "Energy", "Insurance", "Technology"]),
]
ANIMALS = ["Owl", "Heron", "Fox", "Lynx", "Otter", "Falcon", "Wren", "Bison", "Marten", "Ibis", "Crane", "Hare"]


def handle():
    return f"Anon {random.choice(ANIMALS)} {random.randint(10, 99)}"


SESSIONS = {}   # token -> {role, handle, level, senior_id}
THREADS = []


def match_seniors(deal, topic):
    want = set(filter(None, [deal and deal["type"], deal and deal["sector"], topic]))
    scored = sorted(SENIORS, key=lambda s: -len(want & set(s["tags"])))
    return [s["id"] for s in scored[:2]]


# ---------- Sense-style structuring ----------
def structure_reply(question, reply):
    if KEY:
        prompt = (
            "A junior banker asked a senior colleague a question about an M&A deal. Turn the senior's reply into a short "
            "structured result. Return only JSON with keys: answer (1-2 plain sentences, the bottom line), quotes (2-3 "
            "short verbatim phrases from the reply), reasons (2-4 short bullets explaining why), watchouts (1-3 short "
            "bullets: risks or what to double-check). No client names.\n\n"
            f"QUESTION:\n{question}\n\nSENIOR REPLY:\n{reply}"
        )
        try:
            r = httpx.post("https://api.anthropic.com/v1/messages", timeout=40, headers={
                "x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": MODEL, "max_tokens": 700, "messages": [{"role": "user", "content": prompt}]})
            r.raise_for_status()
            txt = "".join(b.get("text", "") for b in r.json()["content"])
            m = re.search(r"\{.*\}", txt, re.S)
            data = json.loads(m.group(0))
            return {k: data.get(k, [] if k != "answer" else "") for k in ("answer", "quotes", "reasons", "watchouts")}
        except Exception as e:
            print("structure_reply fallback:", type(e).__name__, e)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", reply) if s.strip()]
    return dict(answer=" ".join(sents[:1]), quotes=sents[:2], reasons=sents[1:4], watchouts=[])


def summarize(t):
    rs = [r["result"] for r in t["replies"]]
    if not rs:
        return None
    if len(rs) == 1:
        return rs[0]["answer"]
    if KEY:
        try:
            body = "\n\n".join(f"Senior {i+1}: {r['answer']} Reasons: {'; '.join(r['reasons'])}" for i, r in enumerate(rs))
            r = httpx.post("https://api.anthropic.com/v1/messages", timeout=30, headers={
                "x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": MODEL, "max_tokens": 200, "messages": [{"role": "user", "content":
                      f"In 1-2 plain sentences, what do these seniors agree on and where do they differ?\n\n{body}"}]})
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"]).strip()
        except Exception:
            pass
    return " ".join(r["answer"] for r in rs)


# ---------- API ----------
class Login(BaseModel):
    role: str           # "asker" | "senior"
    level: str = ""
    senior_id: str = ""


class AskBody(BaseModel):
    token: str
    question: str
    deal_id: str = ""
    file_ids: list[str] = []
    upload_name: str = ""
    upload_text: str = ""
    topic: str = ""


class ReplyBody(BaseModel):
    token: str
    text: str


def who(token):
    s = SESSIONS.get(token)
    if not s:
        raise HTTPException(401, "Log in again")
    return s


@router.get("/deals")
def deals():
    return [public_deal(d) for d in DEALS]


@router.get("/seniors")
def seniors():
    return SENIORS


@router.post("/login")
def login(b: Login):
    tok = uuid.uuid4().hex
    s = dict(role=b.role, handle=handle(), level=b.level or "Analyst", senior_id=b.senior_id)
    if b.role == "senior":
        sr = next((x for x in SENIORS if x["id"] == b.senior_id), SENIORS[0])
        s.update(senior_id=sr["id"], level=f"{sr['title']} · {sr['desk']}")
    SESSIONS[tok] = s
    return dict(token=tok, **s)


def view(t, s):
    deal = DEAL_BY_ID.get(t["deal_id"])
    senior_view = s["role"] == "senior"
    files = []
    if deal:
        files = [f for f in public_deal(deal, scrubbed=senior_view)["files"] if f["id"] in t["file_ids"]]
    if t.get("upload_name"):
        files.append(dict(id="upload", name=t["upload_name"], text=scrub(t["upload_text"], deal) if senior_view else t["upload_text"]))
    return dict(
        id=t["id"], t=t["t"], topic=t["topic"],
        question=scrub(t["question"], deal) if senior_view else t["question"],
        asker=f"{t['asker_handle']} · {t['asker_level']}",
        mine=t["asker_token"] == s.get("token"),
        deal=public_deal(deal, scrubbed=senior_view) if deal else None,
        files=files, routed=[next(x for x in SENIORS if x["id"] == i) for i in t["routed"]],
        replies=[dict(t=r["t"], by=r["by"], result=r["result"], text=r["text"]) for r in t["replies"]],
        summary=t.get("summary"), waiting=len(t["routed"]) - len(t["replies"]),
    )


@router.get("/threads")
def threads(token: str):
    s = dict(who(token), token=token)
    if s["role"] == "senior":
        mine = [t for t in THREADS if s["senior_id"] in t["routed"]]
    else:
        mine = [t for t in THREADS if t["asker_token"] == token] + [t for t in THREADS if t.get("seed")]
    return [view(t, s) for t in sorted(mine, key=lambda t: -t["t"])]


@router.post("/ask")
def ask(b: AskBody):
    s = who(b.token)
    deal = DEAL_BY_ID.get(b.deal_id)
    t = dict(id=uuid.uuid4().hex[:8], t=time.time(), question=b.question.strip()[:4000], deal_id=b.deal_id,
             file_ids=b.file_ids, upload_name=b.upload_name[:120], upload_text=b.upload_text[:20000],
             topic=b.topic or (deal["type"] if deal else "General"), asker_token=b.token,
             asker_handle=s["handle"], asker_level=s["level"], routed=match_seniors(deal, b.topic), replies=[])
    THREADS.append(t)
    return view(t, dict(s, token=b.token))


@router.post("/threads/{tid}/reply")
def reply(tid: str, b: ReplyBody):
    s = who(b.token)
    t = next((x for x in THREADS if x["id"] == tid), None)
    if not t:
        raise HTTPException(404, "No such question")
    sr = next(x for x in SENIORS if x["id"] == s["senior_id"])
    t["replies"] = [r for r in t["replies"] if r["senior_id"] != sr["id"]]
    t["replies"].append(dict(t=time.time(), senior_id=sr["id"], by=f"{s['handle']} · {sr['title']}, {sr['desk']} · {sr['years']} yrs",
                             text=b.text.strip()[:6000], result=structure_reply(t["question"], b.text)))
    t["summary"] = summarize(t)
    return view(t, dict(s, token=b.token))


# ---------- Seed: two answered questions so the board isn't empty ----------
def _seed():
    THREADS.append(dict(
        id="seed1", t=time.time() - 5400, seed=True, deal_id="ironwood", file_ids=["ironwood-0"], upload_name="", upload_text="",
        topic="LBO", asker_token="", asker_handle="Anon Heron 31", asker_level="Analyst · Leveraged Finance", routed=["s2", "s3"],
        question="On Project Ironwood, why would the sponsor accept a 6-month 101 soft call? Isn't that bad for them if rates fall? I didn't want to ask in the staffing meeting.",
        replies=[dict(t=time.time() - 3600, senior_id="s2", by="Anon Bison 58 · Managing Director, Leveraged Finance · 18 yrs",
                      text="It's the price of getting the deal done at that spread. Investors wanted protection against an immediate repricing. Six months is short, so the sponsor can still reprice next spring. Check the MFN sunset too, that matters more.",
                      result=dict(answer="The soft call is a small concession that buys a tighter spread; six months still lets the sponsor reprice early.",
                                  quotes=["It's the price of getting the deal done at that spread.", "Six months is short"],
                                  reasons=["Lenders wanted protection against an immediate repricing", "A 101 premium for only 6 months costs the sponsor little",
                                           "The sponsor can still reprice once the period ends"],
                                  watchouts=["Check the MFN sunset; it matters more than the soft call"]))],
        summary="The soft call is a small concession that buys a tighter spread; six months still lets the sponsor reprice early."))
    THREADS.append(dict(
        id="seed2", t=time.time() - 1800, seed=True, deal_id="harbor", file_ids=["harbor-0", "harbor-2"], upload_name="", upload_text="",
        topic="Merger", asker_token="", asker_handle="Anon Wren 72", asker_level="Associate · M&A", routed=["s3", "s4"],
        question="Project Harbor crosses the $50B tier. What actually changes for the combined bank the day after close, and what slips first in these integrations?",
        replies=[], summary=None))


_seed()
