# Faceless Story Reel System (Free Stack)

Original playbook for running a **faceless Instagram storytelling page** using **only free tools** — no paid subscriptions required.

This is **not** a copy of any paid PDF. It is a practical system you can run today, built from publicly known creator workflows and current free AI video limits (as of Nov 2026).

## What’s in this folder

| Path | What it is |
|---|---|
| `PLAYBOOK.md` | Full step-by-step system (the “product”) |
| `prompts/` | Copy-paste prompts for research, script, scenes, captions |
| `checklists/daily-reel.md` | One-reel production checklist (~45–60 min) |
| `checklists/account-setup.md` | New page setup before you post |
| `examples/story-brief.example.md` | Filled sample of one reel brief |
| `scripts/new-reel.sh` | Creates a dated folder for each reel |
| `automation/` | CLI that auto-builds a draft Reel MP4 |
| `AUTOMATION.md` | What is automated vs manual, and how to run it |
| `RESOURCES.md` | Free keys, Gemini Pro, Groq, OpenRouter, NotebookLM, Flow |

## Recommended for you (A + C): 30s hook reels

**A** = free card stills (`--images cards`)  
**C** = auto LLM scripts (`--provider auto` → Gemini/Groq/OpenRouter when keys exist)

```bash
# Windows
.\.venv\Scripts\activate
pip install -r requirements.txt

# High-quality ~30s hook script + free still cards + local voice
# Put GEMINI_API_KEY (and optional GROQ/OPENROUTER) in .env
python -m automation --niche "forgotten Indian history" --provider auto --images cards --duration 30 --tts local
```

Without any API key, the same command falls back to offline templates (still ~30s, weaker scripts).

```bash
# Optional: Gemini Pro model explicitly
python -m automation --niche "forgotten Indian history" --provider gemini --model gemini-3.1-pro-preview --images cards --duration 30 --tts local

# Stitch existing stills only
python -m automation stitch --stills "reels\YYYY-MM-DD-title\stills" --seconds 5
```

`--mode` still works as an alias for `--provider`.

Full free-resource guide: [`RESOURCES.md`](RESOURCES.md). Runbook: [`AUTOMATION.md`](AUTOMATION.md).

## Free tool stack (₹0)

| Step | Free tool | Notes |
|---|---|---|
| Research + script | ChatGPT free / Gemini free | Stay under free message limits |
| Still images | Bing Image Creator / Gemini image / Leonardo free credits | Keep a consistent visual style |
| Animate clips | **Google Flow** (best free daily) or **Dreamina** | Flow ≈ 50 credits/day (~4–5 short clips). Avoid peak UTC 14:00–17:00 |
| Edit + captions | CapCut free **or** Instagram Edits | Never use Pro-locked assets (watermark trap) |
| Voice (optional) | CapCut TTS / phone voice / Edge Read Aloud | Faceless = no face; voice optional if you use big on-screen text |
| Audio | Instagram trending audio / CapCut free music | Prefer trending IG audio for reach |
| Publish | Instagram Reels | Post as Reels, not Stories |

**Important:** Free AI video got *worse* in 2026 (Sora gone, many free tiers cut). Plan around **1 solid reel/day**, not 10.

## Start here

1. Read `PLAYBOOK.md`
2. Do `checklists/account-setup.md`
3. Copy prompts from `prompts/`
4. Run one reel with `checklists/daily-reel.md`
5. Repeat daily for 30 days before judging results

## Honest limits

- This system **does not guarantee** views, followers, Meta payouts, or brand deals.
- Story **selection** matters more than tools.
- Free credits, watermarks, and commercial-use rules change — re-check tool terms before monetizing ads.
