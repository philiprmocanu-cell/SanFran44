"""Data guard: scans everything a person types before it can reach the AI.
Anything that looks like bank or customer data is blocked outright, never forwarded."""
import os
import re


def _luhn(num: str) -> bool:
    d = [int(c) for c in num][::-1]
    total = sum(d[0::2]) + sum(sum(divmod(2 * x, 10)) for x in d[1::2])
    return total % 10 == 0


def _aba(num: str) -> bool:
    d = [int(c) for c in num]
    return len(d) == 9 and (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10 == 0


RULES = [
    ("Social Security number", re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"), None),
    ("Card number", re.compile(r"\b(?:\d[ -]?){13,19}\b"), lambda m: _luhn(re.sub(r"\D", "", m))),
    ("Bank routing number", re.compile(r"\b\d{9}\b"), lambda m: _aba(m)),
    ("Account number", re.compile(r"(?i)\b(?:acct|account|a/c|loan)\s*(?:no\.?|number|#|num)?\s*[:#]?\s*\d{6,17}\b"), None),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"), None),
    ("Email address", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), None),
    ("Phone number", re.compile(r"(?<!\d)(?:\+?1[ -.]?)?\(?\d{3}\)?[ -.]\d{3}[ -.]\d{4}(?!\d)"), None),
    ("Confidential marking", re.compile(r"(?i)\b(confidential|internal use only|do not distribute|privileged|non-public|attorney[- ]client|MNPI|customer list|client list)\b"), None),
    ("Pasted spreadsheet / data dump", re.compile(r"(?:[^\n]*[\t,][^\n]*\n){5,}"), None),
]

# A bank adds its own client names and project code names here (comma-separated).
CUSTOM = [t.strip() for t in os.environ.get("GUARD_TERMS", "").split(",") if t.strip()]


def _mask(s: str) -> str:
    s = s.strip()
    return s[:2] + "•" * max(0, len(s) - 4) + s[-2:] if len(s) > 4 else "•" * len(s)


def scan(text: str):
    hits = []
    for name, rx, check in RULES:
        for m in rx.finditer(text):
            if check is None or check(m.group(0) if name != "Card number" else m.group(0)):
                hits.append({"rule": name, "sample": _mask(m.group(0))})
                break
    for term in CUSTOM:
        if re.search(rf"(?i)\b{re.escape(term)}\b", text):
            hits.append({"rule": "Bank's protected term", "sample": _mask(term)})
    return hits


def redact(text: str) -> str:
    """Last line of defence on the way out: mask anything sensitive in the AI's answer."""
    for name, rx, check in RULES[:5]:
        text = rx.sub(lambda m: "[REDACTED]" if (check is None or check(m.group(0))) else m.group(0), text)
    return text
