"""Cross-check every backend endpoint the Flutter app calls against Django URLs.

Run:  python check_routes.py
"""
import os
import re
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DevazBackend.settings")
import django

django.setup()

from django.urls import get_resolver  # noqa: E402

APP = r"M:\MMMMM\msoc\meetsocapp\lib\providers\api_Request.dart"


def collect_patterns(prefix, patterns, out):
    for p in patterns:
        try:
            pat = p.pattern.regex.pattern
        except Exception:
            continue
        if hasattr(p, "url_patterns"):  # URLResolver
            collect_patterns(prefix + pat, p.url_patterns, out)
        else:
            out.append(prefix + pat)


all_patterns = []
collect_patterns("", get_resolver().url_patterns, all_patterns)


def normalize(regex_pat):
    """Turn a Django regex path into a loose glob (leading slash kept out)."""
    s = regex_pat
    for anchor in ("^", "$", r"\Z", r"\A"):
        s = s.replace(anchor, "")
    # (?P<name>...) — any converter (str/uuid/int/slug/...)
    s = re.sub(r"\(\?P<[^>]+>.*?\)", "*", s)
    s = re.sub(r"\([^)]*\)", "*", s)  # anonymous groups / re_path literals
    s = s.replace("\\", "")
    return s.lstrip("/")


route_globs = [normalize(p) for p in all_patterns]


def glob_match(glob, path):
    path = path.lstrip("/")
    rx = "^" + re.escape(glob).replace(r"\*", ".*") + "$"
    return re.match(rx, path) is not None


# ---- endpoints referenced by the Flutter client -----------------------------
src = open(APP, encoding="utf-8").read()
# const/base + 'literal'
base_map = {
    "FinulAllApi": "/meetsoc/",
    "AccountApi": "/account/",
    "ChatApi": "/meetchat/",
}
client = set()

for m in re.finditer(r"\b(FinulAllApi|AccountApi|ChatApi)\s*\+\s*'([^']*)'", src):
    client.add(base_map[m.group(1)] + m.group(2))

# _apiGet('/...') style
for m in re.finditer(r"_api(?:Get|Post|Put|Patch|Delete)\(\s*'([^']*)'", src):
    client.add(m.group(1) if m.group(1).startswith("/") else "/meetsoc/" + m.group(1))

# interpolated templates: `${FinulAllApi}...` / `${ChatApi}conversations/$id/`
for m in re.finditer(r"`([^`]*\$\{(FinulAllApi|AccountApi|ChatApi)\}[^`]*)`", src):
    lit = m.group(1)
    prefix = base_map[m.group(2)]
    lit = lit.replace("${" + m.group(2) + "}", "")
    if lit.startswith("/"):
        lit = lit[1:]
    client.add(prefix + lit)

# plain 'literal with $var' endpoint strings used inside _apiGet / fetch
for m in re.finditer(r"'((?:conversations|calls|posts|comments|stories|groups|pages|users|friends|notifications|watch|search|verification|marketplace|memories|reports|ads|feed|reels|messages)[^']*\$[^']*)'", src):
    client.add("/meetsoc/" + m.group(1))

# ---- report -----------------------------------------------------------------
def strip_query(p):
    return p.split("?", 1)[0]


missing = []
scanned = 0
for raw in sorted(client):
    path = strip_query(raw)
    if "{" in path or not path.strip("/"):
        continue
    if "$ApiLink" in path:
        continue  # artefact of resolveMediaUrl, not an endpoint
    if not path.startswith("/"):
        continue
    scanned += 1
    if any(glob_match(g, path) for g in route_globs):
        continue
    missing.append(path)

print(f"client endpoints scanned: {scanned}")
print(f"django patterns loaded  : {len(all_patterns)}")
print(f"\nUNMATCHED ({len(missing)}):")
for p in missing:
    print("  ", p)
