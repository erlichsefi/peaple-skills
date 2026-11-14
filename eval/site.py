#!/usr/bin/env python3
"""Build the static GitHub Pages site from results/ and skills/.

  python eval/site.py --out _site

Writes index.html (latest run, score trend, skills) and runs/<date>.html for every daily run.
Standard library only.
"""

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arena import ROOT, RESULTS_DIR, load_skills  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "erlichsefi/peaple-skills")
REPO_URL = f"https://github.com/{REPO}"


def e(value):
    return html.escape(str(value or ""))


def load_runs():
    runs = []
    for path in sorted(RESULTS_DIR.glob("*.json")):
        if not re.match(r"\d{4}-\d{2}-\d{2}", path.stem):
            continue  # skip latest.json
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except ValueError:
            pass
    return runs


CSS = """
:root{--blue:#0038b8;--ink:#14213d;--muted:#5c6784;--line:#e3e8f4;--bg:#f7f9fd;--pass:#11804a;--fail:#c2410c}
*{box-sizing:border-box}
body{margin:0;font:16px/1.55 "Rubik",system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--blue)}
.stripe{height:10px;background:linear-gradient(var(--blue) 0 30%,#fff 30% 70%,var(--blue) 70%)}
header,main,footer{max-width:960px;margin:0 auto;padding:0 20px}
header{padding-top:36px;padding-bottom:12px}
header h1{margin:0;font-size:34px;letter-spacing:-.02em}
header p{margin:6px 0 0;color:var(--muted)}
nav{margin-top:14px;display:flex;gap:18px;font-size:15px}
.hero{display:flex;gap:28px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:16px;padding:24px;margin:24px 0}
.score{font-size:64px;font-weight:700;line-height:1;color:var(--blue)}
.score small{font-size:24px;color:var(--muted);font-weight:500}
.meta{color:var(--muted);font-size:14px}
h2{font-size:22px;margin:36px 0 12px}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:4px 18px;margin:0 0 12px}
table{width:100%;border-collapse:collapse;font-size:15px}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:500;font-size:13px;text-transform:uppercase;letter-spacing:.04em}
tr:last-child td{border-bottom:0}
td:first-child code{white-space:nowrap}
.pill{display:inline-block;padding:1px 9px;border-radius:999px;font-size:13px;font-weight:600}
.pass{background:#e3f5ea;color:var(--pass)}
.fail{background:#fdeee5;color:var(--fail)}
code{font:13px ui-monospace,SFMono-Regular,Menlo,monospace;background:#eef2fb;padding:1px 6px;border-radius:6px}
details{border-bottom:1px solid var(--line);padding:12px 0}
details:last-child{border-bottom:0}
summary{cursor:pointer;font-weight:600;list-style:none;display:flex;gap:10px;align-items:center}
summary::-webkit-details-marker{display:none}
blockquote{margin:12px 0;padding:10px 14px;background:var(--bg);border-left:3px solid var(--blue);border-radius:6px}
.agent{white-space:pre-wrap;background:#fff8e6;border-radius:8px;padding:10px 14px}
ul.checks{padding-left:0;list-style:none}
ul.checks li{margin:6px 0}
.wanted li{margin:8px 0}
.chart{width:100%;height:auto;display:block}
.empty{color:var(--muted);padding:18px 0}
footer{color:var(--muted);font-size:14px;padding-top:40px;padding-bottom:40px}
[dir=auto]{unicode-bidi:plaintext}
@media(max-width:600px){.hero{flex-direction:column;align-items:flex-start}.score{font-size:52px}}
"""


def page(title, body, depth=0):
    root = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="stripe"></div>
<header>
  <h1>🇮🇱 peaple-skills arena</h1>
  <p>Agent skills for being an Israeli citizen, tested daily against freshly invented situations.</p>
  <nav><a href="{root}index.html">Latest</a><a href="{root}index.html#history">History</a><a href="{root}index.html#skills">Skills</a><a href="{REPO_URL}">GitHub</a><a href="{REPO_URL}/blob/main/CONTRIBUTING.md">Add a skill</a></nav>
</header>
<main>
{body}
</main>
<footer>Satire. Any resemblance to your building's WhatsApp group is entirely your building's fault.</footer>
</body>
</html>
"""


def pill(passed):
    return '<span class="pill pass">PASS</span>' if passed else '<span class="pill fail">FAIL</span>'


def render_run(run):
    total, passed = run.get("total", 0), run.get("passed", 0)
    pct = round(100 * passed / total) if total else 0
    parts = [f"""
<section class="hero">
  <div class="score">{passed}<small>/{total}</small></div>
  <div>
    <div style="font-size:20px;font-weight:600">{pct}% of scenarios passed</div>
    <div class="meta">Run {e(run.get('date'))} · {e(run.get('skills_count'))} skills · model <code>{e(run.get('model'))}</code> · <code>{e(run.get('scenarios_file'))}</code></div>
  </div>
</section>"""]

    wanted = [r for r in run.get("results", []) if not r.get("passed")]
    if wanted:
        items = []
        for r in wanted:
            s = r.get("suggested_skill") or {}
            items.append(f'<li dir="auto"><strong>{e(r.get("title"))}</strong>: '
                         f'<code>{e(s.get("name", "?"))}</code> {e(s.get("description", ""))}</li>')
        parts.append(f"""
<h2>Skills wanted</h2>
<div class="card"><p class="meta">These scenarios failed. The judge's suggestion is a starting point.
<a href="{REPO_URL}/blob/main/CONTRIBUTING.md">Add a skill</a> and win them back.</p>
<ul class="wanted">{''.join(items)}</ul></div>""")

    details = []
    for r in run.get("results", []):
        skills = " ".join(f"<code>{e(s)}</code>" for s in r.get("skills_loaded", [])) or '<span class="meta">no skills loaded</span>'
        checks = "".join(
            f'<li dir="auto">{"✅" if c.get("met") else "❌"} {e(c.get("expectation"))}'
            f' <span class="meta">({e(c.get("reason"))})</span></li>'
            for c in r.get("expectations", [])
        )
        details.append(f"""
<details>
  <summary>{pill(r.get('passed'))} <span dir="auto">{e(r.get('title'))}</span></summary>
  <blockquote dir="auto">{e(r.get('situation'))}</blockquote>
  <div class="meta">Skills: {skills}</div>
  <p class="agent" dir="auto">{e(r.get('response'))}</p>
  <ul class="checks">{checks}</ul>
</details>""")
    parts.append(f'<h2>Scenarios</h2><div class="card">{"".join(details) or "<p class=empty>No scenarios.</p>"}</div>')
    return "".join(parts)


def render_chart(runs):
    points = [(r["date"], r["passed"] / r["total"]) for r in runs if r.get("total")]
    if len(points) < 2:
        return '<p class="empty">The trend chart appears after two daily runs.</p>'
    w, h, pad = 900, 220, 48
    step = (w - 2 * pad) / (len(points) - 1)
    xy = [(pad + i * step, h - pad - v * (h - 2 * pad)) for i, (_, v) in enumerate(points)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    area = f"{pad},{h - pad} {line} {xy[-1][0]:.1f},{h - pad}"
    grid = "".join(
        f'<line x1="{pad}" x2="{w - pad}" y1="{h - pad - g * (h - 2 * pad):.1f}" y2="{h - pad - g * (h - 2 * pad):.1f}" stroke="#e3e8f4"/>'
        f'<text x="{pad - 8}" y="{h - pad - g * (h - 2 * pad) + 4:.1f}" font-size="12" fill="#5c6784" text-anchor="end">{int(g * 100)}%</text>'
        for g in (0, .5, 1)
    )
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#0038b8"><title>{e(d)}: {round(v * 100)}%</title></circle>'
        for (x, y), (d, v) in zip(xy, points)
    )
    labels = (f'<text x="{pad}" y="{h - 10}" font-size="12" fill="#5c6784">{e(points[0][0])}</text>'
              f'<text x="{w - pad}" y="{h - 10}" font-size="12" fill="#5c6784" text-anchor="end">{e(points[-1][0])}</text>')
    return (f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Pass rate over time">{grid}'
            f'<polygon points="{area}" fill="#0038b8" opacity=".08"/>'
            f'<polyline points="{line}" fill="none" stroke="#0038b8" stroke-width="2.5"/>{dots}{labels}</svg>')


def render_history(runs):
    rows = "".join(
        f'<tr><td><a href="runs/{e(r["date"])}.html">{e(r["date"])}</a></td>'
        f'<td>{r.get("passed", 0)}/{r.get("total", 0)}</td><td>{e(r.get("skills_count"))}</td>'
        f'<td><code>{e(r.get("model"))}</code></td></tr>'
        for r in reversed(runs)
    )
    return (f'<h2 id="history">History</h2><div class="card">{render_chart(runs)}</div>'
            f'<div class="card"><table><tr><th>Run</th><th>Passed</th><th>Skills</th><th>Model</th></tr>'
            f'{rows or "<tr><td colspan=4 class=empty>No runs yet.</td></tr>"}</table></div>')


def render_skills(skills):
    rows = "".join(
        f'<tr><td><a href="{REPO_URL}/blob/main/{e(s["path"])}"><code>{e(s["name"])}</code></a></td>'
        f'<td dir="auto">{e(s["description"])}</td></tr>'
        for s in skills.values()
    )
    return (f'<h2 id="skills">Skills ({len(skills)})</h2><div class="card"><table>'
            f'<tr><th>Skill</th><th>When the agent uses it</th></tr>{rows}</table></div>')


def build(out):
    out = Path(out)
    (out / "runs").mkdir(parents=True, exist_ok=True)
    runs = load_runs()
    skills = load_skills()

    for run in runs:
        (out / "runs" / f"{run['date']}.html").write_text(
            page(f"Arena run {run['date']}", render_run(run), depth=1), encoding="utf-8")

    latest = render_run(runs[-1]) if runs else (
        '<section class="hero"><div><div style="font-size:20px;font-weight:600">No runs yet</div>'
        '<div class="meta">The first daily arena run will appear here.</div></div></section>')
    (out / "index.html").write_text(
        page("peaple-skills arena", latest + render_history(runs) + render_skills(skills)), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Built site with {len(runs)} runs and {len(skills)} skills in {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="_site")
    build(parser.parse_args().out)
