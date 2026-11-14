# Contributing

## The game

Every day the **Arena** asks an LLM to invent fresh everyday Israeli situations, each with the
behavior a stereotypical Israeli would show. Then it runs a simulated agent through them:

1. **Generate**: the generator writes scenarios without knowing which skills exist.
2. **Select**: the agent sees only skill names and descriptions, and picks up to 3 to load (like real agent skills).
3. **Act**: the agent responds using only the loaded skills. With no skill, it behaves like a polite,
   rule-following person from nowhere in particular. It pays full price and goes to the back of the line.
4. **Judge**: a strict judge checks every expected behavior. A scenario passes only if all are met.

Results land in [`results/latest.md`](results/latest.md), with a **Skills wanted** list of what failed
and a suggested skill for each. Your job: add or improve skills until the agent passes.

## Adding a skill

1. Pick something from **Skills wanted** in `results/latest.md`, or your own idea.
2. Create `skills/<kebab-case-name>/SKILL.md`:

   ```markdown
   ---
   name: kebab-case-name
   description: Use whenever ... (this line decides whether the agent loads your skill, so make it specific)
   ---

   # Title

   ## Overview
   ## When to use
   ## Workflow
   ## Common mistakes
   ## Red flags
   ```

3. Add a row to the skills table in `README.md`.
4. Open a PR. The **PR arena** reruns the latest scenarios with your skills and comments the score vs `main`.

Tips:
- **The description matters most.** If the agent never loads your skill, it can't help. Name the concrete situations.
- **Write behaviors that can be seen.** "Sends a DM that says X" beats "is sneaky".
- **Keep it affectionate.** No politics, religion, ethnic stereotypes or real people. Every skill ends
  with a red-flags section where the joke stops (real safety, health, actual corruption).

## Running locally

You need a free API key from any OpenAI-compatible provider. Standard library Python only, nothing to install.

```bash
export LLM_API_KEY=...                       # Gemini API key from Google AI Studio (default provider)
python eval/arena.py evaluate --limit 3      # run the latest scenarios against your skills
python eval/arena.py generate --count 3      # make new scenarios (writes scenarios/<date>.json)
```

Other free providers work by setting two more variables:

| Provider | `LLM_BASE_URL` | Example `LLM_MODEL` |
|---|---|---|
| Gemini (default) | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-flash-latest` |
| Groq | `https://api.groq.com/openai/v1` | `openai/gpt-oss-120b` |
| OpenRouter | `https://openrouter.ai/api/v1` | any `:free` model |

Free tiers have per-minute limits, so the runner waits `LLM_MIN_INTERVAL` seconds between calls (default 7).

## Repo setup (maintainers)

- Add a repository secret `LLM_API_KEY`.
- Optional repository variables `LLM_BASE_URL` and `LLM_MODEL` to switch provider or model.
- PRs from forks don't get secrets, so the PR arena skips them. A maintainer can run it locally,
  or the next daily run will score the merged skills.
