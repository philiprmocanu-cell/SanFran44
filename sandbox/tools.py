"""Public-data tools. Every request leaves through the egress firewall (HTTPS_PROXY);
the sandbox network has no other route out."""
import html
import re
import time

import httpx

UA = "LedgerCheck research demo contact@ledgercheck.dev"
_cache: dict = {}


def _client():
    # A fresh client per call: no cookies, no saved logins, like a logged-out browser.
    return httpx.Client(headers={"User-Agent": UA, "Accept-Encoding": "gzip"}, timeout=20, follow_redirects=True)


def _get_json(url):
    if url in _cache:
        return _cache[url]
    with _client() as c:
        r = c.get(url)
        r.raise_for_status()
        _cache[url] = r.json()
        return _cache[url]


def find_company(name: str):
    data = _get_json("https://www.sec.gov/files/company_tickers.json")
    q = name.strip().lower()
    hits = []
    for row in data.values():
        title, ticker = row["title"], row["ticker"]
        if q == ticker.lower() or q in title.lower():
            hits.append({"name": title, "ticker": ticker, "cik": row["cik_str"]})
    hits.sort(key=lambda h: (h["ticker"].lower() != q, len(h["name"])))
    return {"matches": hits[:8]} if hits else {"matches": [], "note": "No SEC registrant matched. Try the ticker."}


CONCEPTS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "RevenuesNetOfInterestExpense", "InterestAndDividendIncomeOperating"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "receivables": ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"],
    "inventory": ["InventoryNet"],
    "payables": ["AccountsPayableCurrent", "AccountsPayableAndAccruedLiabilitiesCurrent"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "loans": ["LoansAndLeasesReceivableNetReportedAmount", "FinancingReceivableExcludingAccruedInterestAfterAllowanceForCreditLoss"],
    "loan_loss_allowance": ["FinancingReceivableAllowanceForCreditLossExcludingAccruedInterest", "AllowanceForLoanAndLeaseLosses"],
}


def _annual(facts, names):
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for n in names:
        units = gaap.get(n, {}).get("units", {}).get("USD")
        if not units:
            continue
        by_year = {}
        for u in units:
            if u.get("form") not in ("10-K", "10-K/A") or u.get("fp") != "FY":
                continue
            if "start" in u:  # duration facts must cover about a year
                days = (time.mktime(time.strptime(u["end"], "%Y-%m-%d")) - time.mktime(time.strptime(u["start"], "%Y-%m-%d"))) / 86400
                if not 330 <= days <= 380:
                    continue
            year = int(u["end"][:4])
            prev = by_year.get(year)
            if prev is None or u["filed"] >= prev["filed"]:
                by_year[year] = {"val": u["val"], "end": u["end"], "filed": u["filed"], "form": u["form"], "accn": u["accn"]}
        if by_year:
            return n, dict(sorted(by_year.items())[-4:])
    return None, {}


def _growth(series, y):
    a, b = series.get(y), series.get(y - 1)
    if not a or not b or not b["val"]:
        return None
    return (a["val"] - b["val"]) / abs(b["val"])


def get_financials(cik: int):
    facts = _get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json")
    out, series = {"company": facts.get("entityName"), "cik": int(cik), "years": {}}, {}
    for key, names in CONCEPTS.items():
        concept, s = _annual(facts, names)
        if s:
            series[key] = s
            for y, v in s.items():
                out["years"].setdefault(str(y), {})[key] = v["val"]
            out.setdefault("sources", {})[key] = {"concept": concept, "latest_filing": list(s.values())[-1]["accn"]}
    years = sorted(int(y) for y in out["years"])
    flags = []
    if years:
        y = years[-1]
        out["latest_fiscal_year"] = y
        ni = series.get("net_income", {}).get(y, {}).get("val")
        cfo = series.get("operating_cash_flow", {}).get(y, {}).get("val")
        assets = series.get("total_assets", {})
        if ni and cfo is not None and ni > 0:
            ratio = cfo / ni
            if ratio < 0.8:
                flags.append({"check": "Profit not turning into cash", "detail": f"Operating cash flow is {ratio:.0%} of net income in FY{y}.", "severity": "high" if ratio < 0.5 else "medium"})
        if ni is not None and cfo is not None and assets.get(y) and assets.get(y - 1):
            avg = (assets[y]["val"] + assets[y - 1]["val"]) / 2
            accr = (ni - cfo) / avg
            if accr > 0.08:
                flags.append({"check": "High accruals (Sloan ratio)", "detail": f"(Net income - operating cash flow) / average assets = {accr:.1%}.", "severity": "medium"})
        g_rev = _growth(series.get("revenue", {}), y)
        g_ni, g_cfo = _growth(series.get("net_income", {}), y), _growth(series.get("operating_cash_flow", {}), y)
        if g_ni is not None and g_cfo is not None and g_ni > 0.1 and g_cfo < 0:
            flags.append({"check": "Profit up, cash down", "detail": f"Net income grew {g_ni:.0%} while operating cash flow fell {abs(g_cfo):.0%}.", "severity": "high"})
        for key, label, gap in (("receivables", "Customers owe more, faster than sales grow", 0.15), ("inventory", "Inventory piling up faster than sales", 0.15), ("payables", "Bills to suppliers stretching (possible hidden financing)", 0.25)):
            g = _growth(series.get(key, {}), y)
            if g is not None and g_rev is not None and g - g_rev > gap:
                flags.append({"check": label, "detail": f"{key.capitalize()} grew {g:.0%} vs revenue {g_rev:.0%} in FY{y}.", "severity": "medium"})
        loans, allow_ = series.get("loans", {}), series.get("loan_loss_allowance", {})
        if loans.get(y) and allow_.get(y) and loans.get(y - 1) and allow_.get(y - 1):
            r1, r0 = allow_[y]["val"] / loans[y]["val"], allow_[y - 1]["val"] / loans[y - 1]["val"]
            if r1 < r0 * 0.85:
                flags.append({"check": "Loan-loss reserve shrinking", "detail": f"Reserve fell from {r0:.2%} to {r1:.2%} of loans; check whether earnings were helped by releasing reserves.", "severity": "medium"})
    out["red_flags"] = flags or [{"check": "No numeric red flags", "detail": "None of the automated checks fired for the latest year.", "severity": "none"}]
    return out


def get_filing_history(cik: int):
    sub = _get_json(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
    r = sub.get("filings", {}).get("recent", {})
    rows = list(zip(r.get("form", []), r.get("filingDate", []), r.get("items", [""] * len(r.get("form", []))), r.get("accessionNumber", [])))
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 3 * 365 * 86400))
    events = []
    for form, date, items, accn in rows:
        if date < cutoff:
            continue
        if form.startswith("NT "):
            events.append({"date": date, "form": form, "meaning": "Late filing notice: the company missed a reporting deadline.", "accn": accn})
        if form.startswith("8-K") and "4.01" in (items or ""):
            events.append({"date": date, "form": form, "meaning": "Item 4.01: change of auditor.", "accn": accn})
        if form.startswith("8-K") and "4.02" in (items or ""):
            events.append({"date": date, "form": form, "meaning": "Item 4.02: past financial statements can no longer be relied on (restatement).", "accn": accn})
        if form in ("10-K/A", "10-Q/A"):
            events.append({"date": date, "form": form, "meaning": "Amended report.", "accn": accn})
    return {"company": sub.get("name"), "sic": sub.get("sicDescription"), "warning_events_last_3_years": events[:20] or "none found"}


def fetch_public_page(url: str):
    try:
        with _client() as c:
            r = c.get(url)
    except httpx.ProxyError:
        return {"url": url, "result": "BLOCKED by the container firewall. This site is not on the public-data allowlist."}
    except Exception as e:
        return {"url": url, "result": f"Could not reach the page ({type(e).__name__}). The container can only reach allowlisted public sites."}
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", r.text)
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))).strip()
    return {"url": str(r.url), "status": r.status_code, "text": text[:5000]}


TOOLS = [
    {"name": "find_company", "description": "Look up a public company's SEC CIK number by name or ticker.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "get_financials", "description": "Pull the last 4 fiscal years of reported financials from SEC XBRL filings and run automated red-flag checks (cash vs profit, accruals, receivables/inventory/payables vs revenue, loan-loss reserves).", "input_schema": {"type": "object", "properties": {"cik": {"type": "integer"}}, "required": ["cik"]}},
    {"name": "get_filing_history", "description": "List warning events in the last 3 years of SEC filings: late filings, auditor changes, restatements, amended reports.", "input_schema": {"type": "object", "properties": {"cik": {"type": "integer"}}, "required": ["cik"]}},
    {"name": "fetch_public_page", "description": "Open a public web page in a logged-out, cookie-free reader. Only allowlisted public sites are reachable; anything else is blocked by the firewall.", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
]
RUN = {"find_company": find_company, "get_financials": get_financials, "get_filing_history": get_filing_history, "fetch_public_page": fetch_public_page}
