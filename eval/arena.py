#!/usr/bin/env python3
"""The Arena: generate daily scenarios and check whether the skills make the agent behave as expected.

Commands:
  generate   Ask the LLM for new scenarios and save them to scenarios/<date>.json
  evaluate   Run every scenario through the agent + judge and write a report

Works with any OpenAI-compatible chat completions endpoint. Configure with env vars:
  LLM_API_KEY    (required)
  LLM_BASE_URL   default: NVIDIA build (https://integrate.api.nvidia.com/v1), free tier
  LLM_MODEL      optional comma-separated preference list; otherwise picked from the live model list
  LLM_TIMEOUT    seconds to wait for one reply, default 240
  LLM_MIN_INTERVAL  seconds between calls, default 2 (NVIDIA free tier is ~40 requests/minute)

Standard library only, so it runs anywhere without installing anything.
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
SCENARIOS_DIR = ROOT / "scenarios"
RESULTS_DIR = ROOT / "results"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
# Free-tier catalogs change often. Models named in LLM_MODEL are tried first (if still listed);
# after that the runner picks chat models from the endpoint's live /models list, in this order.
DEFAULT_MODELS = ""
PREFERRED_PATTERNS = [
    r"llama-3\.3-70b", r"llama-4", r"qwen3.*(instruct|a\d+b)", r"nemotron.*(super|nano)", r"flash",
    r"deepseek-v\d", r"mistral-(medium|small)", r"gemma", r"glm", r"kimi", r"mistral-large", r"gpt-oss",
    r"nemotron", r"llama.*(70b|8b)", r"instruct",
]
NON_CHAT = re.compile(r"embed|rerank|guard|safety|reward|vision|-vl|vlm|parse|ocr|clip|retriev|coder|"
                      r"translate|asr|tts|audio|image|detector|pii|nemoretriever|bge|e5-|sdxl|flux", re.I)


def rank_catalog(ids):
    ranked = []
    for pattern in PREFERRED_PATTERNS:
        for model_id in sorted(ids, reverse=True):  # reverse: newer versions tend to sort later
            if model_id not in ranked and not NON_CHAT.search(model_id) and re.search(pattern, model_id, re.I):
                ranked.append(model_id)
    return ranked
MAX_SKILLS_PER_SCENARIO = 3


# ---------------------------------------------------------------- LLM client

def env(name, default=""):
    value = os.environ.get(name, "").strip()
    return value or default


class LLM:
    def __init__(self):
        self.api_key = env("LLM_API_KEY")
        if not self.api_key:
            sys.exit("LLM_API_KEY is not set. See CONTRIBUTING.md for free providers.")
        self.base_url = env("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.min_interval = float(env("LLM_MIN_INTERVAL", "2"))
        self.timeout = float(env("LLM_TIMEOUT", "240"))
        configured = [m.strip() for m in env("LLM_MODEL", DEFAULT_MODELS).split(",") if m.strip()]
        catalog = self.list_models()
        if catalog:
            print(f"Endpoint lists {len(catalog)} models", file=sys.stderr)
            listed = [m for m in configured if m in catalog]
            candidates = listed + [m for m in rank_catalog(catalog) if m not in listed][:25]
        else:
            candidates = configured
        if not candidates:
            sys.exit("No usable model: set LLM_MODEL (the endpoint did not return a model list).")
        self.models = self.probe(candidates)
        if not self.models:
            sys.exit("None of the candidate models answered. Set LLM_MODEL to a model that works on your key.")
        print(f"Using: {', '.join(self.models)}", file=sys.stderr)
        self.model = self.models[0]
        self._last_call = 0.0
        self.calls = 0

    def probe(self, candidates, want=4, timeout=45):
        """Free tiers list many models that are 404 or stuck in a queue. Send each a tiny request and
        keep the ones that actually answer, fastest first."""
        answered = []
        for model in candidates:
            request = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps({"model": model, "max_tokens": 16,
                                 "messages": [{"role": "user", "content": "Reply with OK."}]}).encode(),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            started = time.time()
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    json.load(response)
                latency = time.time() - started
                answered.append((latency, model))
                print(f"  probe {model}: {latency:.1f}s", file=sys.stderr)
            except urllib.error.HTTPError as error:
                print(f"  probe {model}: HTTP {error.code}", file=sys.stderr)
                if error.code == 429:
                    time.sleep(10)
            except Exception as error:
                print(f"  probe {model}: {type(error).__name__}", file=sys.stderr)
            if len(answered) >= want:
                break
            time.sleep(self.min_interval)
        return [model for _, model in sorted(answered)]

    def list_models(self):
        request = urllib.request.Request(f"{self.base_url}/models",
                                         headers={"Authorization": f"Bearer {self.api_key}"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return {m["id"] for m in json.load(response).get("data", []) if m.get("id")}
        except Exception as error:  # some providers don't expose /models; fall back to LLM_MODEL
            print(f"Could not list models: {error}", file=sys.stderr)
            return set()

    def chat(self, messages, temperature=0.2):
        wait = self.min_interval - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)

        attempt = 0
        while True:
            request = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps({
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 2048,
                }).encode(),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            self._last_call = time.time()
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = json.load(response)
                self.calls += 1
                content = data["choices"][0]["message"].get("content") or ""
                # reasoning models may include their thinking inline
                return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            except urllib.error.HTTPError as error:
                detail = error.read().decode(errors="replace")[:500]
                if error.code in (400, 403, 404, 410, 422) and len(self.models) > 1 and (
                        error.code in (404, 410) or "model" in detail.lower() or "function" in detail.lower()):
                    dropped = self.models.pop(0)
                    self.model = self.models[0]
                    print(f"  model {dropped} unavailable (HTTP {error.code}), switching to {self.model}",
                          file=sys.stderr)
                    continue
                if error.code in (429, 500, 502, 503, 504) and attempt < 5:
                    retry_after = error.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else 10 * 2 ** attempt
                    print(f"  LLM HTTP {error.code}, retrying in {delay:.0f}s", file=sys.stderr)
                    time.sleep(delay)
                    attempt += 1
                    continue
                raise RuntimeError(f"LLM request failed: HTTP {error.code}: {detail}") from error
            except (TimeoutError, ConnectionError) as error:
                # slow or overloaded model: try once more, then move to the next candidate
                if attempt < 1:
                    attempt += 1
                    print(f"  {self.model} timed out, retrying", file=sys.stderr)
                    continue
                if len(self.models) > 1:
                    dropped = self.models.pop(0)
                    self.model = self.models[0]
                    attempt = 0
                    print(f"  model {dropped} too slow ({error}), switching to {self.model}", file=sys.stderr)
                    continue
                raise RuntimeError(f"LLM request failed: {error}") from error
            except urllib.error.URLError as error:
                if attempt < 5:
                    time.sleep(10 * 2 ** attempt)
                    attempt += 1
                    continue
                raise RuntimeError(f"LLM request failed: {error}") from error


def extract_json(text):
    """Pull the first JSON object out of a model reply (handles ```json fences and chatter)."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object in reply: {text[:200]!r}")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj


def ask_json(llm, prompt, temperature=0.2, retries=2):
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(retries + 1):
        reply = llm.chat(messages, temperature=temperature)
        try:
            return extract_json(reply)
        except ValueError:
            if attempt == retries:
                raise
            messages += [
                {"role": "assistant", "content": reply},
                {"role": "user", "content": "That was not valid JSON. Reply with the JSON object only."},
            ]


def prompt(name, **values):
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").format(**values)


# ---------------------------------------------------------------- skills

def parse_frontmatter(text):
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def load_skills():
    skills = {}
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        name = meta.get("name") or path.parent.name
        skills[name] = {
            "name": name,
            "description": meta.get("description", ""),
            "content": text,
            "path": str(path.relative_to(ROOT)),
        }
    return skills


# ---------------------------------------------------------------- generate

def recent_titles(days=7):
    titles = []
    for path in sorted(SCENARIOS_DIR.glob("*.json"))[-days:]:
        try:
            titles += [s["title"] for s in json.loads(path.read_text(encoding="utf-8"))["scenarios"]]
        except (KeyError, ValueError):
            pass
    return titles


def cmd_generate(args):
    llm = LLM()
    titles = recent_titles()
    titles_text = "\n".join(f"- {t}" for t in titles) or "- (none yet)"
    raw_scenarios = []
    remaining = args.count
    while remaining > 0:  # small batches keep each reply short enough for slow free endpoints
        batch = min(4, remaining)
        known = titles + [str(r.get("title", "")) for r in raw_scenarios]
        known_text = "\n".join(f"- {t}" for t in known) or titles_text
        data = ask_json(llm, prompt("generator", count=batch, recent_titles=known_text), temperature=1.0)
        raw_scenarios += data.get("scenarios", [])[:batch]
        remaining -= batch

    scenarios, seen = [], set()
    for raw in raw_scenarios:
        if not raw.get("situation") or not raw.get("expected_behaviors"):
            continue
        sid = re.sub(r"[^a-z0-9-]+", "-", str(raw.get("id") or raw.get("title", "scenario")).lower()).strip("-")
        while sid in seen:
            sid += "-x"
        seen.add(sid)
        scenarios.append({
            "id": sid,
            "title": str(raw.get("title", sid)),
            "situation": str(raw["situation"]),
            "expected_behaviors": [str(b) for b in raw["expected_behaviors"]][:3],
            "tags": [str(t) for t in raw.get("tags", [])],
        })

    if not scenarios:
        sys.exit("Generator returned no usable scenarios.")

    SCENARIOS_DIR.mkdir(exist_ok=True)
    out = SCENARIOS_DIR / f"{args.date}.json"
    out.write_text(json.dumps({
        "date": args.date,
        "model": llm.model,
        "scenarios": scenarios,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(scenarios)} scenarios to {out.relative_to(ROOT)}")


# ---------------------------------------------------------------- evaluate

def run_scenario(llm, skills, scenario):
    catalog = "\n".join(f"- {s['name']}: {s['description']}" for s in skills.values()) or "- (no skills yet)"
    selection = ask_json(llm, prompt(
        "selector", skills=catalog, situation=scenario["situation"], max_skills=MAX_SKILLS_PER_SCENARIO,
    ))
    chosen = [n for n in selection.get("skills", []) if n in skills][:MAX_SKILLS_PER_SCENARIO]

    loaded = "\n\n".join(skills[n]["content"] for n in chosen) or "(none)"
    response = llm.chat([
        {"role": "system", "content": prompt("agent", skills=loaded)},
        {"role": "user", "content": (
            f"{scenario['situation']}\n\n"
            "What do you do? Answer in first person, under 150 words. "
            "Quote any message you send exactly."
        )},
    ], temperature=0.4).strip()

    expected = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(scenario["expected_behaviors"]))
    verdict = ask_json(llm, prompt("judge", situation=scenario["situation"], response=response, expected=expected))
    checks = verdict.get("expectations", [])
    passed = bool(checks) and len(checks) >= len(scenario["expected_behaviors"]) and all(c.get("met") for c in checks)

    return {
        "id": scenario["id"],
        "title": scenario["title"],
        "situation": scenario["situation"],
        "skills_loaded": chosen,
        "selection_reason": selection.get("reason", ""),
        "response": response,
        "expectations": checks,
        "passed": passed,
        "suggested_skill": None if passed else verdict.get("suggested_skill"),
    }


def latest_scenarios_file():
    files = sorted(SCENARIOS_DIR.glob("*.json"))
    return files[-1] if files else None


def render_markdown(report):
    total, passed = report["total"], report["passed"]
    lines = [
        f"# Arena results: {report['date']}",
        "",
        f"**{passed}/{total} scenarios passed** with {report['skills_count']} skills "
        f"(model `{report['model']}`, scenarios `{report['scenarios_file']}`).",
        "",
        "| | Scenario | Skills loaded |",
        "|---|---|---|",
    ]
    for r in report["results"]:
        mark = "✅" if r["passed"] else "❌"
        skills = ", ".join(f"`{s}`" for s in r["skills_loaded"]) or "none"
        lines.append(f"| {mark} | {r['title']} | {skills} |")

    wanted = [r for r in report["results"] if not r["passed"]]
    if wanted:
        lines += ["", "## Skills wanted", "",
                  "Add a skill that makes these pass. The judge's suggestion is a starting point, not a rule.", ""]
        for r in wanted:
            suggestion = r.get("suggested_skill") or {}
            lines.append(f"- **{r['title']}**: `{suggestion.get('name', '?')}`: {suggestion.get('description', '')}")

    lines += ["", "## Details", ""]
    for r in report["results"]:
        mark = "✅" if r["passed"] else "❌"
        lines += [f"### {mark} {r['title']}", "", f"> {r['situation']}", "", "**Agent:**", "", r["response"], ""]
        for c in r["expectations"]:
            lines.append(f"- {'✅' if c.get('met') else '❌'} {c.get('expectation', '')}: {c.get('reason', '')}")
        lines.append("")
    return "\n".join(lines)


def cmd_evaluate(args):
    path = Path(args.scenarios) if args.scenarios else latest_scenarios_file()
    if not path or not path.exists():
        sys.exit("No scenarios found. Run `generate` first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    scenarios = data["scenarios"][: args.limit] if args.limit else data["scenarios"]

    llm = LLM()
    skills = load_skills()
    print(f"Evaluating {len(scenarios)} scenarios from {path.name} with {len(skills)} skills")

    results = []
    for scenario in scenarios:
        try:
            result = run_scenario(llm, skills, scenario)
        except Exception as error:  # one broken scenario should not sink the whole run
            print(f"  ! {scenario['id']}: {error}", file=sys.stderr)
            result = {"id": scenario["id"], "title": scenario["title"], "situation": scenario["situation"],
                      "skills_loaded": [], "selection_reason": "", "response": f"(error: {error})",
                      "expectations": [], "passed": False, "suggested_skill": None, "error": True}
        print(f"  {'PASS' if result['passed'] else 'FAIL'}  {scenario['title']}")
        results.append(result)

    report = {
        "date": args.date,
        "scenarios_file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "model": llm.model,
        "skills_count": len(skills),
        "total": len(results),
        "passed": sum(r["passed"] for r in results),
        "results": results,
    }
    markdown = render_markdown(report)

    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(markdown + "\n")
    if args.markdown_out:
        Path(args.markdown_out).write_text(markdown + "\n", encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.save:
        RESULTS_DIR.mkdir(exist_ok=True)
        payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        (RESULTS_DIR / f"{args.date}.json").write_text(payload, encoding="utf-8")
        (RESULTS_DIR / "latest.json").write_text(payload, encoding="utf-8")
        (RESULTS_DIR / "latest.md").write_text(markdown + "\n", encoding="utf-8")
        history = RESULTS_DIR / "history.csv"
        new_file = not history.exists()
        with history.open("a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["date", "passed", "total", "skills", "model", "scenarios_file"])
            writer.writerow([args.date, report["passed"], report["total"], len(skills), llm.model,
                             report["scenarios_file"]])

    print(f"\n{report['passed']}/{report['total']} passed ({llm.calls} LLM calls)")


# ---------------------------------------------------------------- main

def main():
    try:
        from zoneinfo import ZoneInfo
        today = dt.datetime.now(ZoneInfo("Asia/Jerusalem")).date().isoformat()
    except Exception:
        today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate today's scenarios")
    gen.add_argument("--count", type=int, default=8)
    gen.add_argument("--date", default=today)
    gen.set_defaults(func=cmd_generate)

    ev = sub.add_parser("evaluate", help="run scenarios through the agent and judge")
    ev.add_argument("--scenarios", help="scenario file (default: latest in scenarios/)")
    ev.add_argument("--date", default=today)
    ev.add_argument("--limit", type=int, help="only run the first N scenarios")
    ev.add_argument("--save", action="store_true", help="write results/ files (daily run)")
    ev.add_argument("--summary", help="append the markdown report to this file (e.g. $GITHUB_STEP_SUMMARY)")
    ev.add_argument("--markdown-out", help="write the markdown report to this file")
    ev.add_argument("--json-out", help="write the JSON report to this file")
    ev.set_defaults(func=cmd_evaluate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
