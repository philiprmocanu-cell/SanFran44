"""Egress firewall: the ONLY way out of the sandbox network.

HTTPS CONNECT to an allowlisted host is tunneled; everything else gets 403
and is logged. A tiny JSON log is served on :8889 for the gateway's audit view.
"""
import asyncio
import json
import os
import time
from collections import deque

ALLOW = [h.strip().lower() for h in open(os.environ.get("ALLOWLIST", "/app/allowlist.txt")) if h.strip() and not h.startswith("#")]
LOG = deque(maxlen=300)


def allowed(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host == a or host.endswith("." + a) for a in ALLOW)


def record(host, port, verdict):
    LOG.append({"t": time.time(), "host": host, "port": port, "verdict": verdict})
    print(f"[egress] {verdict.upper():7} {host}:{port}", flush=True)


async def pipe(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def handle(reader, writer):
    try:
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
    except Exception:
        writer.close()
        return
    line = head.split(b"\r\n", 1)[0].decode("latin-1")
    parts = line.split()
    if len(parts) < 2:
        writer.close()
        return
    method, target = parts[0].upper(), parts[1]
    if method != "CONNECT":
        # Plain HTTP is never allowed out: no unencrypted channel.
        host = target.split("/")[2] if "://" in target else target
        record(host, 80, "blocked")
        writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        writer.close()
        return
    host, _, port = target.rpartition(":")
    port = int(port or 443)
    if port != 443 or not allowed(host):
        record(host, port, "blocked")
        writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        writer.close()
        return
    try:
        up_r, up_w = await asyncio.wait_for(asyncio.open_connection(host, port), 10)
    except Exception:
        record(host, port, "error")
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        writer.close()
        return
    record(host, port, "allowed")
    writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    await writer.drain()
    await asyncio.gather(pipe(reader, up_w), pipe(up_r, writer))


async def log_server(reader, writer):
    try:
        await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
    except Exception:
        pass
    body = json.dumps({"allowlist": ALLOW, "events": list(LOG)}).encode()
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body)
    await writer.drain()
    writer.close()


async def main():
    s1 = await asyncio.start_server(handle, "0.0.0.0", 8888)
    s2 = await asyncio.start_server(log_server, "0.0.0.0", 8889)
    print(f"[egress] allowlist: {ALLOW}", flush=True)
    async with s1, s2:
        await asyncio.gather(s1.serve_forever(), s2.serve_forever())


asyncio.run(main())
