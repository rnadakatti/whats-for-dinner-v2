# 🍽️ What's for Dinner? v2 — API Edition

**Live demo:** https://whats-for-dinner-v2-kq5ajd9gnqcz6zpy4qsvnx.streamlit.app

A meal suggestion tool built with direct Anthropic API integration, engineered system prompts, structured JSON output, and a two-layer eval system. This is the second version of the same product — the first was vibe coded in Sprint 0. This version demonstrates what's actually happening under the hood.

---

## What It Does

Enter the ingredients you have at home → get 3 structured meal suggestions, each with cook time, difficulty, a missing ingredient to pick up, why it works with your ingredients, and an allergen flag.

Two modes:
- **Classic** — familiar, reliable dishes most home cooks already know
- **Surprise Me** — unexpected combinations you wouldn't think of yourself

Optional allergy/avoid field — Claude respects it across all suggestions.

---

## Why I Built It This Way

This is the second version of the same concept. Sprint 0 built it using Replit Agent and Lovable — vibe coded, shipped in one session, two live URLs. Sprint 1 rebuilt it from scratch with direct API access.

The comparison is the point:

| | v1 (Sprint 0) | v2 (Sprint 1) |
|---|---|---|
| How built | Vibe coded | Direct Anthropic API + Python |
| Prompt control | None — black box | Full — engineered system prompt |
| Output format | Unstructured text | Structured JSON → formatted UI cards |
| Observability | None | PromptLayer logging on every call |
| Evals | None | Role-based + LLM-as-judge |

Sprint 0 taught what the product should do. Sprint 1 taught how it actually works.

---

## Key Technical Decisions

**Two separate system prompts — not one with a toggle**

Classic and Surprise Me use entirely different system prompts with different constraints. Classic restricts to widely available ingredients and familiar dishes. Surprise Me actively pushes for unexpected combinations. One prompt trying to do both produced mediocre results for both. Two prompts produce distinctly different, high-quality outputs for each mode.

**Structured JSON enforced at the prompt level**

The system prompt defines a strict 6-field JSON schema. Claude returns raw JSON — no markdown, no prose. The UI parses each field and renders it differently: cook time as a metric, difficulty as a badge, reason as prose. This only works because the output is consistent and parseable every time.

The first version of the prompt didn't include "no markdown, no code blocks." Claude wrapped JSON in backticks, breaking `json.loads()`. The fix went into the prompt, not the code — context engineering, not code patching.

**Eval layer built in from day one**

Two evals run on every submission:
- **Role-based eval** — five deterministic checks: 3 meals returned, all 6 fields present, no empty fields, valid difficulty values, allergy flag present. Catches structural failures.
- **LLM-as-judge eval** — scores quality, mode appropriateness, and practical usefulness on a 1-10 scale with reasoning. Catches qualitative failures.

Key finding: LLM-as-judge systematically miscounts sentences. Quantitative checks belong in role-based evals. Qualitative checks belong in the judge. Use the right tool for the right job.

---

## What the Eval Caught

Running Classic mode with "chicken, garlic, lemon, olive oil, pasta," the judge scored 8/10 and flagged: *"Classic mode is a slight stretch since galangal and lemongrass are somewhat niche ingredients."*

This is an actionable product insight — the Classic system prompt needs tighter constraints on what counts as a widely available ingredient. The eval caught a real quality issue that the role-based checks missed entirely.

---

## AgentOps Thinking

**What breaks at scale:**
At 1,000 concurrent users, each submission makes 2 API calls (main + judge eval). Current code has no retry logic for 529 overload errors. In production this needs exponential backoff and graceful degradation.

**How I'd monitor it:**
PromptLayer logs every call with latency and tags. Key metrics to watch: average response latency (spike = API slowdown), judge score distribution (drop = prompt degradation), error rate (spike = API or input issues).

**The HITL question:**
Wrong meal suggestions are low-stakes — no human approval needed before showing results. The HITL checkpoint that adds value: a "flag this result" button feeding back into prompt refinement.

**What I'd add with a database:**
Save liked recipes per user. Personalise future suggestions based on cooking history. The current tool is stateless — every session starts fresh. Persistent history is where the value compounds.

---

## Tech Stack

| Layer | Tool |
|---|---|
| LLM | Anthropic Claude (claude-sonnet-4-6) |
| API | Anthropic Messages API (direct) |
| UI | Streamlit |
| Observability | PromptLayer |
| Language | Python |
| Deployment | Streamlit Community Cloud |
| Version control | GitHub |

---

## Running Locally

**1. Clone the repo**
```bash
git clone https://github.com/rnadakatti/whats-for-dinner-v2.git
cd whats-for-dinner-v2
```

**2. Install dependencies**
```bash
pip3 install -r requirements.txt
```

**3. Set up environment variables**

Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your-anthropic-key
PROMPTLAYER_API_KEY=your-promptlayer-key
```

**4. Run the app**
```bash
python3 -m streamlit run whats_for_dinner_ui.py
```

Opens at `http://localhost:8501`

---

## Project Context

Built as part of a structured AI learning sprint program focused on AgentOps and AI Product Operations. Each sprint applies an operational lens to what was built: what breaks at scale, how to monitor it, where humans need to be in the loop.

This project is Sprint 1 of 6. Sprint 0 was vibe coding. Sprint 1 is direct API integration. Sprint 3 adds RAG and a database. Sprint 4 adds agents.

---

*Built by Rohit Nadakatti — March 2026*
