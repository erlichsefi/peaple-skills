# peaple-skills 🇮🇱

Agent skills for being an Israeli citizen.

Modern AI agents get skills: neat folders with a `SKILL.md` that teach them how to do one thing well.
Israeli citizens have skills too. Nobody wrote them down. Until now.

> This is satire. Any resemblance to your building's WhatsApp group is entirely your building's fault.

## Skills

| Skill | What it does |
|---|---|
| [ask-to-be-excused](skills/ask-to-be-excused/SKILL.md) | When a rule is announced to a group, privately DM the person who announced it and ask to be excused. |
| [not-written-not-forbidden](skills/not-written-not-forbidden/SKILL.md) | If a rule doesn't explicitly forbid it, it's allowed. Find the gray area and move in. |
| [hold-the-line](skills/hold-the-line/SKILL.md) | Rejoin any queue at the front with "אני רק שאלה" and "הייתי פה לפני". |
| [know-a-guy](skills/know-a-guy/SKILL.md) | Before any bureaucratic task, find someone who knows someone. The official channel is the fallback. |
| [expert-on-everything](skills/expert-on-everything/SKILL.md) | Confident opinions on every topic. Experience optional, "תאמין לי" mandatory. |
| [haggle-everything](skills/haggle-everything/SKILL.md) | Every price is an opening offer. Never be the פראייר. |
| [bring-cake-say-no-cake](skills/bring-cake-say-no-cake/SKILL.md) | As host: "אל תביאו כלום". As guest: never arrive empty-handed. Both at once. |
| [ma-pitom](skills/ma-pitom/SKILL.md) | Reject every suggestion with "מה פתאום", then adopt it a week later as your own idea. |
| [lo-nora](skills/lo-nora/SKILL.md) | Incident response: "לא נורא", "יהיה בסדר", no postmortem. |

## The Arena 🏟️

Every day an LLM invents new everyday Israeli situations, along with how a true Israeli would react.
A simulated agent then faces them with only the skills in this repo. A strict judge scores the result.

Without skills, the agent is a polite, rule-following person who pays full price and waits at the back of the line.
Every skill you add makes it a little more Israeli.

- Today's score and the **Skills wanted** list: [`results/latest.md`](results/latest.md)
- Score over time: [`results/history.csv`](results/history.csv)
- How it works and how to add a skill: [CONTRIBUTING.md](CONTRIBUTING.md)

## Structure

Each skill lives in its own folder:

```
skills/
  <skill-name>/
    SKILL.md   # frontmatter (name, description) + instructions
eval/          # the arena runner and its prompts
scenarios/     # generated scenarios, one file per day
results/       # daily scores
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), then open a PR. If your PR is rejected, please DM the maintainer and explain that your case is different.
