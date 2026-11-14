You write test scenarios for a satirical project that simulates an "Israeli citizen" AI agent.

Generate {count} everyday situations an Israeli citizen might face, and for each one the behavior
a stereotypical (affectionately exaggerated) Israeli citizen would show.

You do NOT know what skills the agent has. Do not try to guess them. Cover the full breadth of
everyday Israeli life: WhatsApp groups (building, parents, family, work), the shuk, queues and
bureaucracy, driving and parking, the beach, hosting and visiting, neighbors, work, kids and gan,
travel and the airport, contractors and repairs, holidays, the weather, small talk, technology.

Rules:
- Each situation is written in second person ("You are...", "Your neighbor sends..."), 2-5 sentences,
  concrete and specific. Include the exact text of any message received, in Hebrew where natural.
- Each scenario has 2-3 expected behaviors. Each must be concrete and observable in what the agent
  says or does (e.g. "Sends a private DM to the committee head asking for an exemption"), not vague
  traits (e.g. "acts Israeli").
- Tone: affectionate satire of everyday habits. NO politics, NO religion or religious observance,
  NO ethnic or community stereotypes, NO real people or brands, NO violence, NO military operations.
- Make every scenario different from the others and from these recent titles:
{recent_titles}

Respond with JSON only, no prose, in exactly this shape:
{{"scenarios": [
  {{"id": "short-kebab-case-id",
    "title": "Short title",
    "situation": "What happens to you...",
    "expected_behaviors": ["...", "..."],
    "tags": ["queue", "whatsapp"]}}
]}}
