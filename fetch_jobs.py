"""Daily skill-based job feed for Hyderabad (4 yrs experience).
Source: Adzuna India API (free key). Output: docs/index.html
"""
import os, re, json, html, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

APP_ID = os.environ["ADZUNA_APP_ID"]
APP_KEY = os.environ["ADZUNA_APP_KEY"]

LOCATION = "Hyderabad"
MY_EXP = 4            # years
EXP_TOLERANCE = 2     # keep jobs asking for 2 to 6 years
MAX_DAYS_OLD = 3
MIN_SCORE = 2         # how many skill points a job needs to appear

# Skill -> points. Edit freely.
SKILLS = {
    "sql": 2, "power bi": 2, "excel": 1, "tableau": 2, "python": 1,
    "fp&a": 3, "fpa": 3, "financial planning": 3, "budgeting": 2,
    "forecasting": 2, "variance analysis": 3, "mis": 2, "reporting": 1,
    "financial analysis": 3, "accounting": 2, "general ledger": 2,
    "reconciliation": 1, "p&l": 2, "dashboard": 1, "data analysis": 2,
    "financial modeling": 2, "business analysis": 1,
}

# Search queries are built from skills, not job titles.
QUERIES = [
    "sql power bi financial analysis",
    "fp&a variance analysis budgeting forecasting",
    "excel mis reporting accounting dashboard",
    "tableau python financial reporting",
    "financial modeling data analysis p&l",
]

def fetch(query):
    params = {
        "app_id": APP_ID, "app_key": APP_KEY, "results_per_page": 50,
        "what_or": query, "where": LOCATION, "distance": 30,
        "max_days_old": MAX_DAYS_OLD, "sort_by": "date",
        "content-type": "application/json",
    }
    url = "https://api.adzuna.com/v1/api/jobs/in/search/1?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r).get("results", [])
    except Exception as e:
        print("fetch failed:", query, e)
        return []

def score(text):
    t = text.lower()
    hits = [s for s in SKILLS if s in t]
    return sum(SKILLS[s] for s in hits), hits

def exp_ok(text):
    t = text.lower()
    m = re.search(r"(\d+)\s*(?:\+|-|to|–)?\s*(\d+)?\s*(?:years|yrs|year)", t)
    if not m:
        return True
    lo = int(m.group(1)); hi = int(m.group(2) or lo)
    return lo <= MY_EXP + EXP_TOLERANCE and hi >= MY_EXP - EXP_TOLERANCE

jobs = {}
for q in QUERIES:
    for j in fetch(q):
        text = f"{j.get('title','')} {j.get('description','')}"
        sc, hits = score(text)
        if sc < MIN_SCORE or not exp_ok(text):
            continue
        jobs[j["id"]] = {
            "title": j.get("title", ""),
            "company": (j.get("company") or {}).get("display_name", "Unknown"),
            "loc": (j.get("location") or {}).get("display_name", LOCATION),
            "url": j.get("redirect_url", "#"),
            "date": j.get("created", "")[:10],
            "score": sc, "skills": hits,
        }

ranked = sorted(jobs.values(), key=lambda x: (x["date"], x["score"]), reverse=True)
ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

rows = "\n".join(
    f'<li><a href="{html.escape(j["url"])}" target="_blank" rel="noopener">{html.escape(j["title"])}</a>'
    f'<div class="meta">{html.escape(j["company"])} · {html.escape(j["loc"])} · {j["date"]}</div>'
    f'<div class="tags">{"".join(f"<span>{html.escape(s)}</span>" for s in j["skills"][:8])}</div></li>'
    for j in ranked
) or "<li>No matching jobs today.</li>"

page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Jobs – Hyderabad</title>
<style>
:root{{--bg:#fff;--fg:#1a1a1a;--mut:#666;--card:#f5f5f7;--tag:#e3ecff;--tagfg:#1d3f8f;--link:#0b57d0}}
@media(prefers-color-scheme:dark){{:root{{--bg:#16181d;--fg:#eee;--mut:#9aa;--card:#21242b;--tag:#26365e;--tagfg:#bcd0ff;--link:#8ab4f8}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font-family:system-ui,sans-serif;max-width:760px;margin:auto}}
h1{{font-size:1.3rem}} .sub{{color:var(--mut);font-size:.85rem}}
ul{{list-style:none;padding:0}} li{{background:var(--card);padding:12px 14px;margin:10px 0;border-radius:10px}}
a{{color:var(--link);font-weight:600;text-decoration:none}} .meta{{color:var(--mut);font-size:.85rem;margin:4px 0}}
.tags span{{display:inline-block;background:var(--tag);color:var(--tagfg);border-radius:6px;padding:2px 7px;margin:2px 4px 0 0;font-size:.75rem}}
</style></head><body>
<h1>Data / FP&amp;A jobs · {LOCATION}</h1>
<div class="sub">{len(ranked)} matches · last {MAX_DAYS_OLD} days · matched on skills · updated {ist:%d %b %Y, %I:%M %p} IST</div>
<ul>{rows}</ul></body></html>"""

os.makedirs("docs", exist_ok=True)
open("docs/index.html", "w", encoding="utf-8").write(page)
print("Saved", len(ranked), "jobs")
