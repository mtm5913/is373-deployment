"""Build the static specification without third-party packages."""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def build():
    parts, paragraph, listing = [], [], []
    list_kind = None
    def inline(text):
        safe = escape(text)
        return re.sub(r"https://[^\s<>]+", lambda match: '<a href="'+match[0]+'">'+match[0]+'</a>', safe)
    def flush():
        nonlocal list_kind
        if paragraph:
            parts.append("<p>"+inline(" ".join(paragraph))+"</p>")
            paragraph.clear()
        if listing:
            parts.append("<"+list_kind+">"+"".join("<li>"+inline(item)+"</li>" for item in listing)+"</"+list_kind+">")
            listing.clear()
            list_kind = None
    for line in (ROOT/"docs/SPECIFICATION.md").read_text().splitlines():
        if not line.strip():
            flush()
        elif line.startswith("# "):
            flush()
        elif line.startswith("## "):
            flush()
            parts.append("<h2>"+escape(line[3:])+"</h2>")
        elif line.startswith("- ") or re.match(r"^\d+\. ", line):
            kind = "ul" if line.startswith("- ") else "ol"
            if list_kind and list_kind != kind:
                flush()
            list_kind = kind
            listing.append(re.sub(r"^(?:- |\d+\. )", "", line))
        else:
            if listing: flush()
            paragraph.append(line)
    flush()
    template = (ROOT/"scripts/spec-template.html").read_text()
    (ROOT/"docs/index.html").write_text(template.replace("{{CONTENT}}","".join(parts)))

if __name__ == "__main__":
    build()
