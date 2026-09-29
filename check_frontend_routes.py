"""Cross-check every backend endpoint the Next.js site calls against Django URLs.

Run:  python check_frontend_routes.py   (from DevazBackend/)
"""
import os
import re

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DevazBackend.settings")
import django

django.setup()

from django.urls import get_resolver  # noqa: E402

FRONT = r"M:\MMMMM\msoc\meetsoc_frontend"


def collect(prefix, patterns, out):
    for p in patterns:
        try:
            pat = p.pattern.regex.pattern
        except Exception:
            continue
        if hasattr(p, "url_patterns"):
            collect(prefix + pat, p.url_patterns, out)
        else:
            out.append(prefix + pat)


def normalize(regex_pat):
    s = regex_pat
    for anchor in ("^", "$", r"\Z", r"\A"):
        s = s.replace(anchor, "")
    s = re.sub(r"\(\?P<[^>]+>.*?\)", "*", s)
    s = re.sub(r"\([^)]*\)", "*", s)
    s = s.replace("\\", "")
    return s.lstrip("/")


all_patterns = []
collect("", get_resolver().url_patterns, all_patterns)
route_globs = [normalize(p) for p in all_patterns]


def glob_match(glob, path):
    rx = "^" + re.escape(glob).replace(r"\*", ".*") + "$"
    return re.match(rx, path.lstrip("/")) is not None


client = set()
for root, _dirs, files in os.walk(FRONT):
    if any(part in root for part in ("node_modules", ".next", ".git")):
        continue
    for f in files:
        if not f.endswith((".ts", ".tsx")):
            continue
        src = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r"[\"'`]((?:/)?(?:meetsoc|account|meetchat)/[^\"'`\s]*)[\"'`]", src):
            p = m.group(1)
            if not p.startswith("/"):
                p = "/" + p
            # keep the path but turn `${...}` interpolations into wildcards
            p = re.sub(r"\$\{[^}]*\}", "*", p)
            client.add(p)

missing = []
scanned = 0
for raw in sorted(client):
    path = raw.split("?", 1)[0]
    if not path.strip("/") or "*" in path and path.endswith("*") is False:
        pass
    if path.rstrip("/").endswith("$") or "${" in path:
        continue
    scanned += 1
    variants = [path, path if path.endswith("/") else path + "/"]
    if any(glob_match(g, v) for v in variants for g in route_globs):
        continue
    missing.append(path)

print(f"frontend endpoints scanned: {scanned}")
print(f"django patterns loaded    : {len(all_patterns)}")
print(f"\nUNMATCHED ({len(missing)}):")
for p in missing:
    print("  ", p)
