import json
import os
import time
from datetime import datetime, timezone
from urllib import robotparser
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fastembed import TextEmbedding

import config

HEADERS = {"User-Agent": config.USER_AGENT}

def load_robots(url):
    """Read the site's robots.txt so we only fetch what is allowed."""
    p = urlparse(url)
    rp = robotparser.RobotFileParser()
    resp = requests.get(f"{p.scheme}://{p.netloc}/robots.txt", headers=HEADERS, timeout=20)
    rp.parse(resp.text.splitlines() if resp.status_code == 200 else [])
    return rp

def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text

def extract(html):
    """Return (page title, [(tag, text), ...]) with menus, scripts, footers removed."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "header", "footer", "nav", "form", "noscript", "iframe", "svg", "aside"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else "PlacidWay page"
    root = soup.find("main") or soup.body
    lines, last = [], None
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "tr"]):
        if el.name == "tr":   # keep table rows together: "Treatment | Price | Includes"
            cells = [c.get_text(" ", strip=True) for c in el.find_all(["th", "td"])]
            text = " | ".join(c for c in cells if c)
        else:
            text = " ".join(el.get_text(" ", strip=True).split())
        if text and text != last:      # skip empty and duplicate lines
            lines.append((el.name, text))
            last = text
    return title, lines

def make_chunks(title, lines, max_chars=900):
    """Group lines under their nearest heading; each chunk is about one section."""
    chunks, buf, heading = [], [], title

    def flush():
        if buf:
            chunks.append(f"{title} > {heading}\n" + "\n".join(buf))
            buf.clear()

    for tag, text in lines:
        if tag in ("h1", "h2", "h3", "h4"):
            flush()
            heading = text
            continue
        if sum(len(b) for b in buf) + len(text) > max_chars:
            flush()
        buf.append(text)
    flush()
    return chunks

def build_index():
    """Full refresh: crawl → clean → chunk → embed → save. Returns a summary."""
    os.makedirs("data", exist_ok=True)
    rp = load_robots(config.URLS[0])
    chunks, report = [], []

    for url in config.URLS:
        if not rp.can_fetch(config.USER_AGENT, url):
            report.append(f"SKIPPED (robots.txt): {url}")
            continue
        try:
            title, lines = extract(fetch(url))
        except requests.RequestException as e:
            report.append(f"FAILED: {url} ({e})")
            continue
        page_chunks = make_chunks(title, lines)
        report.append(f"{len(page_chunks):3d} chunks  {url}")
        chunks += [{"url": url, "title": title, "text": t} for t in page_chunks]
        time.sleep(config.REQUEST_DELAY)          # ~1 request per second

    if not chunks:
        raise RuntimeError("No content ingested.\n" + "\n".join(report))

    model = TextEmbedding(config.EMBED_MODEL)
    vectors = list(model.embed([c["text"] for c in chunks]))
    for c, v in zip(chunks, vectors):
        c["embedding"] = [round(float(x), 5) for x in v]

    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(config.INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump({"built_at": built_at, "chunks": chunks}, f)

    # Human-readable dump so you can eyeball extraction quality
    with open("data/chunks_preview.txt", "w", encoding="utf-8") as f:
        for i, c in enumerate(chunks):
            f.write(f"--- CHUNK {i} | {c['url']}\n{c['text']}\n\n")

    return {"built_at": built_at, "chunks": len(chunks), "report": report}


if __name__ == "__main__":
    summary = build_index()
    print("\n".join(summary["report"]))
    print(f"Done: {summary['chunks']} chunks, built {summary['built_at']}")