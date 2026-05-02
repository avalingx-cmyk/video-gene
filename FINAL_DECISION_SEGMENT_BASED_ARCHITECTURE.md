# Final Decision: Segment-Based Layered Video Generation Architecture

> **Date:** 2026-05-02  
> **Author:** Megatron (Strategic Command)  
> **Scope:** DIN-64 — Video Generation Architecture Decision  
> **Status:** Ready for approval

---

## Executive Decision

After extensive R&D across multiple agents (Research, Soundblaster, Barricade), we have a clear winner:

> **Adopt the Segment-Based Layered Workflow**  
> Generate 5–15s video segments via AI → overlay text, TTS, and music programmatically → user edits in a browser canvas → FFmpeg exports final 1080p MP4.

This replaces the previous "full sequential video" plan entirely.

---

## 1. Why the Old Plan Failed

The original concept tried to generate a single long video (30s–5min) and overlay everything on top.

| Problem | Why It Breaks |
|---|---|
| **Full-video generation degrades after 10–15s** | No free API supports >15s in one call. Quality collapses: motion coherence, character consistency, and scene logic all degrade. |
| **Text in prompts = garbled output** | AI video models render text as visual noise. "Title: Introduction" emerges as misspelled, unaligned gibberish. |
| **No review workflow** | One-shot generation means if the output is bad, the entire job is wasted. |
| **Audio sync is guesswork** | TTS + background music overlaid on a finished video requires manual alignment with no timeline. |
| **No editing after generation** | Cannot change titles, transitions, or audio without regenerating everything. |

**Verdict:** The old plan is technically infeasible at $0 budget and produces poor UX.

---

## 2. Why the New Plan Wins

The segment-based layered approach splits each layer (video, text, audio, transitions) into independently generated components, then composites them with a user-editing layer.

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: AI Video Footage (no text in prompt)      │  ← Happy Horse / Luma / Runway
│  Layer 2: Text Overlays (titles, CTAs, brand)       │  ← GPT-4 script + Canvas overlay
│  Layer 3: TTS Voiceover (per-segment narration)    │  ← Groq Orpheus "qrog"
│  Layer 4: Background Music (auto-selected)          │  ← Suno / royalty-free
│  Layer 5: Transitions (fade / wipe / slide)       │  ← FFmpeg / Remotion
└─────────────────────────────────────────────────────┘
                        ↓
           Browser Canvas Editor (like Canva)
           ├── Drag text positions
           ├── Adjust timing, font, color
           ├── Preview scrubber (360p low-res)
           └── User approves → export
                        ↓
           FFmpeg composes 1080p MP4 (final)
```

### Core Improvement: Each Layer is Best-of-Breed

| Layer | Tool | Why This Tool |
|---|---|---|
| **Video footage** | Happy Horse via fal.ai (primary), Luma Ray2, Runway Gen-4.5 | #1 ranked, 1080p+audio native, 9:16 portrait, 15s max per segment |
| **Video script / titles** | GPT-4 / Claude | Best marketing/educational copy; outputs JSON with timestamps |
| **TTS voiceover** | Groq Orpheus "qrog" | Fastest generation, supports `[cheerful]`, `[whisper]` vocal tags, included with Groq API |
| **Fallback TTS** | ElevenLabs, Fish Speech | ElevenLabs = quality; Fish Speech = open-source, 80+ languages, $0 |
| **Background music** | Suno API / MiniMax Music / royalty-free library | Auto-selected by content type (educational = calm, marketing = upbeat) |
| **Transitions** | FFmpeg `xfade` / Remotion `<Sequence>` | Fade, wipe, slide between segments |
| **Text overlay engine** | Browser Canvas 2D (preview) + FFmpeg `drawtext` (export) | Same JSON drives both; zero cost; WYSIWYG |
| **Audio mixing** | FFmpeg `sidechaincompress` | Professional ducking: music dips when TTS speaks |

### Key Benefit: The User Sees a Preview Before Export

With the old plan: prompt → wait 5 minutes → bad video → retry.
With the new plan: prompt → segments generate in parallel → browser editor opens → user adjusts text/timing → preview at 360p → approve → 1080p export.

---

## 3. Technical Stack (Zero Budget)

| Component | Technology | Cost |
|---|---|---|
| Backend | Python 3.11 + FastAPI + Celery + Redis | $0 |
| Job queue | Redis + Celery (async processing, retries) | $0 |
| Frontend editor | React + Next.js + HTML5 Canvas 2D | $0 |
| Video generation | Happy Horse via fal.ai (free credits on signup) | $0 |
| Fallback video | Luma Ray2, Runway Gen-4.5, Kling 3 | Pay-per-use if primary quota exhausted |
| TTS (primary) | Groq Orpheus "qrog" | Included with Groq API |
| TTS (fallback) | Fish Speech (self-hosted) / ElevenLabs free tier | $0 |
| BGM | Suno API / MiniMax Music v2.5 / royalty-free | $0 |
| Video composition | FFmpeg (server-side) + Canvas 2D (browser) | $0 |
| Audio mixing | FFmpeg `sidechaincompress` + `amix` | $0 |
| Text overlay | FFmpeg `drawtext` or ASS subtitles | $0 |
| Preview | HTML5 `<video>` + Canvas overlay | $0 |
| Export | FFmpeg 1080p H.264 AAC | $0 |
| Storage | Cloudflare R2 (generous free egress) | $0 |
| Database | PostgreSQL (metadata, user projects) | $0 |
| Deployment | Railway / Render free tier | $0 |

---

## 4. Workflow Detail

### Step 1: User Input
- Text prompt or .md/.pdf upload
- Optional: brand logo, color palette, font preference

### Step 2: AI Planning (Backend)
- GPT-4 splits prompt into 3–5 segment scripts (5–15s each)
- Generates per-segment:
  - Video description (no text — pure footage)
  - Narration script
  - Title + CTA text + position
  - Transition type

### Step 3: Parallel Generation (Celery + Redis)
- **Video**: Happy Horse generates each segment independently
- **Audio**: Groq Orpheus generates TTS per segment
- **Music**: Suno generates background track matching content mood
- Each job tracked independently with retry + provider fallback

### Step 4: Browser Editor Opens
- Low-res 360p preview for fast iteration
- Layer panel: video segments, text layers, audio tracks, transitions
- Canvas: user drags text, resizes, changes font/color
- Timeline scrubber: jump to any segment
- Actions: reorder segments, regenerate a segment, change transition

### Step 5: User Approves → FFmpeg Export
- Backend receives JSON of all edits
- FFmpeg composites:
  - Concatenate segments with transitions
  - Burn text overlays at exact positions/times
  - Mix TTS + BGM with sidechain ducking
  - Output: 1080×1920 H.264 AAC MP4

### Step 6: Publishing (Optional)
- YouTube Data API: upload + schedule
- n8n webhook: trigger automation
- Direct MP4 download

---

## 5. Risk & Mitigation

| Risk | Mitigation |
|---|---|
| Higher API cost (3–5× more calls) | Free tiers cover initial testing; Fish Speech replaces paid TTS; rate limiting per user |
| Implementation complexity | Existing FastAPI + Celery scaffold already in place; Canvas 2D is standard browser tech |
| Preview ≠ final mismatch | Same JSON drives Canvas preview and FFmpeg export; coordinates identical |
| Segment inconsistency (character drift between clips) | Reference image per segment (Happy Horse supports 1–9 reference images); last-frame conditioning |
| Audio sync issues | Per-segment TTS generated separately; FFmpeg concatenates with exact timestamps |

---

## 6. Comparison: Old vs. New

| Criteria | Full-Video (Old) | Segment-Based Layered (New) | Winner |
|---|---|---|---|
| Video length | 30s–5min (APIs limit to 10–15s) | 30s–5min (by stitching segments) | **New** |
| Quality | Degrades after 10s | Optimal at 5–15s per segment | **New** |
| Text quality | Garbled, unreadable | Crisp, brand-perfect typography | **New** |
| Brand control | Random colors/fonts | Exact brand colors/fonts | **New** |
| Editability | None (one-shot) | Full Canva-style editor | **New** |
| Audio sync | Manual, error-prone | Precise per-segment mixing | **New** |
| Review workflow | None | 360p preview → edit → export | **New** |
| Fault tolerance | All-or-nothing | Regenerate 1 segment only | **New** |
| API cost | 1 call/video | 3–5 calls/video | Old (cheaper) |
| UX | Prompt → wait → video | Prompt → segments → edit → video | **New** |

> The 3–5× API cost increase is justified by dramatically better UX, quality, reliability, and user retention.

---

## 7. Open Questions for User

Before implementation begins, the following questions need clarification:

1. **Brand logo handling**: Should the system auto-detect brand colors from a logo upload, or does the user input hex codes manually?
2. **Font library**: Use Google Fonts (free) or support custom brand font uploads?
3. **Template system**: Pre-built templates for educational/marketing/tech (like Canva), or start from scratch every time?
4. **Music licensing**: Use AI-generated music (Suno — no copyright issues) or a licensed royalty-free library (Epidemic Sound, Artlist)?
5. **Export options**: MP4 only, or also GIF/WebM for social platforms?
6. **Editor budget**: Are we committing to the $0 FFmpeg + Canvas stack, or is there budget for Remotion ($100/mo) for professional preview/export?
7. **Video generation budget**: If free credits run out, should we cap per-user generation or ask for payment?

---

## 8. Implementation Phase 1 Prototype (If Approved)

**Goal**: Validate the architecture with a working end-to-end prototype in 1 week.

**Deliverables:**
- [ ] Generate 1 video segment with Happy Horse (no text, clean footage)
- [ ] Generate 1 title + script with GPT-4
- [ ] Generate 1 TTS clip with Groq Orpheus
- [ ] Composite with FFmpeg (text overlay + audio mix)
- [ ] Show in a simple browser page with Canvas overlay
- [ ] Let user drag text position
- [ ] Export final 1080p MP4

**Team assignment:**
- **Soundblaster (engineer)**: FFmpeg composition pipeline, Happy Horse API integration
- **Barricade (QA)**: Validate segment quality, test audio sync, verify export fidelity
- **Megatron (you)**: Strategic oversight, blockers, approval gates

---

## 9. Research Artifacts

All supporting research is documented in the project:

| Document | Content |
|---|---|
| `RESEARCH_SEGMENT_VS_FULL.md` | Detailed comparison of segment-based vs. full-video generation |
| `RESEARCH_LAYERED_VIDEO_EDITOR.md` | Layered architecture for text overlay, audio mixing, and editor design |
| `AI_VIDEO_EDITOR_STACK_REPORT_2026.md` | 2026-era tool comparison: Remotion, Shotstack, FFmpeg, Cloudinary, Canvas |
| `budget-text-overlay-research.md` | $0 text overlay stack: Canvas + FFmpeg + shared JSON model |
| `RESEARCH_ANSWERS.md` | Resolutions to question.md items: copyright, misuse prevention, API 9:16 support, "qrog" identity |
| `question.md` | Full Q&A with user requirements (updated) |
| `plan.md` | Updated project plan (segment-based workflow) |
| `implementation.md` | Implementation roadmap with phases |

---

## Recommendation

**Approve this architecture and authorize Phase 1 prototype development.**

The segment-based layered workflow is the only viable path for $0-cost, high-quality, editable video generation at 30s–5min lengths. All other approaches either exceed budget, produce unreadable text, or lack user review.

Next step after approval: create child issues for Soundblaster (prototype build) and Barricade (quality validation).

---

*Prepared by: Megatron, Supreme Commander*  
*Date: 2026-05-02*