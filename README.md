# Ledger Check: a sealed AI analyst for banks

Banks ban AI tools because staff can paste customer data into them. Ledger Check is an AI credit analyst that physically can't touch bank data:

- **Sealed container.** The AI runs on a network with no route to the internet. Its only exit is a firewall that allows public SEC filings and the AI provider, nothing else.
- **No bank files.** Nothing is mounted in. The disk is read-only, and it runs without admin rights.
- **Logged-out browser.** Every web request is a fresh session with no cookies or sign-ins.
- **Data guard.** Every question is scanned before it reaches the AI. SSNs, card numbers, routing and account numbers, emails, phone numbers, "confidential" markings, pasted spreadsheets and the bank's own protected terms are blocked outright.
- **Audit log.** Every question, block and firewall decision is recorded.

## Run it

Needs Docker and an `ANTHROPIC_API_KEY` in `.env`.

```bash
docker compose up -d --build
```

Then open http://localhost:8080

### Or as a Mac app

```bash
./macapp/build.sh
```

This builds **Ledger Check.app** and installs it in /Applications. Opening it starts Docker (OrbStack or Docker Desktop) if needed, builds and seals the containers, and shows the app in its own window. On first launch it asks for an Anthropic API key, which is saved only on that Mac. Quitting the app stops the containers.

Needs Xcode command line tools (`xcode-select --install`).

## Demo script (2 minutes)

1. **Check a borrower.** Real SEC numbers, red flags, and what to ask next.
2. **Paste customer data.** Blocked before the AI ever sees it.
3. **Reach the bank's intranet.** The AI tries, and the firewall blocks it. The audit log shows it.
4. **Run isolation test.** The container tries to break out 9 ways and fails every time.

## Parts

| Folder | What it is |
|---|---|
| `gateway/` | The app and data guard: the only door in |
| `sandbox/` | The AI analyst: sealed network, read-only, no mounts |
| `egress/` | The firewall, with the allowlist in `egress/allowlist.txt` |

Add a bank's client names or project code names to `GUARD_TERMS` in `docker-compose.yml`.
