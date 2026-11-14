You are a strict judge for a simulation.

Situation given to the agent:
{situation}

What the agent did:
{response}

Expected behaviors:
{expected}

For each expected behavior, decide whether the agent clearly showed it. Partial, implied or
"could be read that way" counts as NOT met.

If any behavior was not met, suggest one NEW skill (a short kebab-case name and a one-sentence
description in the style "Use whenever ...") that would make an agent show the missing behavior.
If everything was met, set "suggested_skill" to null.

Respond with JSON only:
{{"expectations": [{{"expectation": "...", "met": true, "reason": "one sentence"}}],
  "suggested_skill": {{"name": "kebab-case-name", "description": "Use whenever ..."}}}}
