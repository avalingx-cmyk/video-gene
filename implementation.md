# Implementation Plan for Video Generator — New Architecture

> **Status:** Plan mode — awaiting approval before implementation  
> **Date:** 2026-05-02  

## Overview

User inputs a prompt. System creates a video. Simple.

Cloud-native API service that transforms text prompts, markdown documents, and images into publish-ready vertical videos (1080×1920) for YouTube Shorts, TikTok, and Instagram Reels. **Zero GPU cost** — all generation via 2026-era cloud APIs.

## The New Idea: How It Works

1. **User inputs a prompt** (text, .md, .pdf, or image reference)
2. **System processes the prompt** — splits into segments, generates each layer:
   - **Video layer:** AI video model (Happy Horse / Luma / Runway) generates 5–15s clean footage segments — NO text in video prompts
   - **Text layer:** GPT-4 / Claude generates titles, CTAs, and scripts
   - **Audio layer:** Groq Orpheus "qrog" generates TTS voiceover per segment
   - **Music layer:** Suno / MiniMax generates background music matched to content type
3. **User reviews in a browser Canvas editor** — drag text, adjust timing, edit audio, change transitions, preview at 360p
4. **User approves → FFmpeg exports** final 1080×1920 MP4 with all layers composed
5. **Optional:** Upload to YouTube, trigger n8n workflow, download

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Web App)                          │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Prompt Input     │  │ File Upload  │  │ Image Reference        │  │
│  │ (text/md/pdf)    │  │ (.md, .pdf)  │  │ (image-to-video)       │  │
│  └────────┬─────────┘  └──────┬───────┘  └───────────┬───────────┘  │
│           └───────────────────┼──────────────────────┘              │
│                               ▼                                     │
│              ┌────────────────────────────────────┐                 │
│              │  Canvas Editor UI                  │                 │
│              │  - <video> + Canvas overlay        │                 │
│              │  - Drag text (Canva-like)          │                 │
│              │  - Timeline scrubber               │                 │
│              │  - Transition selector             │                 │
│              │  - 360p preview → Approve → Export │                 │
│              └────────────────┬───────────────────┘                 │
└───────────────────────────────┼─────────────────────────────────────┘
                                │ HTTP
┌───────────────────────────────▼─────────────────────────────────────┐
│                      Backend (Python FastAPI)                       │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Input Parser — text, .md, .pdf, image uploads               │  │
│  └──────────────┬───────────────────────────────────────────────┘  │
│                 ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Content Filter — block 18+, harmful, no text in video prompts│  │
│  └──────────────┬───────────────────────────────────────────────┘  │
│                 ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  AI Planning Layer (GPT-4 / Claude)                           │  │
│  │  - Split prompt into 3-5 segments (5-15s each)               │  │
│  │  - Generate per-segment:                                      │  │
│  │    • Video description (NO text — pure footage)               │  │
│  │    • Narration script for TTS                                 │  │
│  │    • Title + CTA text + position                              │  │
│  │    • Transition type                                           │  │
│  └──────────────┬───────────────────────────────────────────────┘  │
│                 ▼ (parallel generation, tracked by Celery + Redis)  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PARALLEL GENERATION LAYERS                                   │  │
│  │                                                                │  │
│  │  ┌─────────────────┐  ┌─────────────┐  ┌───────────────────┐  │  │
│  │  │ Video Layer      │  │ Audio Layer  │  │ Music Layer       │  │  │
│  │  │ Happy Horse API   │  │ Groq Orpheus │  │ Suno / MiniMax    │  │  │
│  │  │ (primary)         │  │ TTS "qrog"   │  │ (auto-matched)    │  │  │
│  │  │ Luma, Runway,     │  │ ElevenLabs,  │  │ Royalty-free      │  │  │
│  │  │ Kling (fallback)  │  │ FishSpeech   │  │ library           │  │  │
│  │  │                   │  │              │  │                   │  │  │
│  │  │ 5-15s segments    │  │ Per-segment  │  │ Mood-matched      │  │  │
│  │  │ 1080×1920 9:16    │  │ Voiceover    │  │ to content type   │  │  │
│  │  └────────┬──────────┘  └──────┬───────┘  └───────┬───────────┘  │  │
│  └───────────┼────────────────────┼──────────────────┼─────────────┘  │
│              └────────────────────┼──────────────────┘                │
│                                   ▼                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  FFmpeg Composition & Export                                  │  │
│  │  - Concatenate segments with xfade transitions               │  │
│  │  - Burn text overlays (drawtext / ASS subtitles)             │  │
│  │  - Mix TTS + BGM with sidechain ducking                      │  │
│  │  - Output: 1080×1920 H.264 AAC MP4                          │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                        Integrations                                  │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ YouTube API      │  │ n8n Webhook  │  │ Cloud Storage (R2)    │  │
│  │ (schedule upload)│  │ / Automation │  │ (segments + finals)   │  │
│  └──────────────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Requirements (from question.md)

| Requirement | Value |
|---|---|
| Video length | 30 seconds to 5+ minutes (via 3–20 segments of 5–15s) |
| Resolution | 1080×1920 (9:16 portrait) |
| Audio | TTS voiceover + background music |
| Voiceover languages | English (Groq Orpheus), 32+ (ElevenLabs), 80+ (Fish Speech) |
| Voice style | Natural/conversational (ed) + professional (mkt/tech) + vocal tags ([cheerful], [whisper]) |
| Content types | Educational, marketing, technology |
| Prompt complexity | Both simple and complex |
| Target audience | Parents, kids, social media users, YouTube creators |
| Interface | Canvas-based editor: drag text, timeline, transitions, preview |
| Output format | MP4 only |
| Post-generation editing | Full: drag text, adjust timing, transitions, reorder, regenerate segments |
| Deployment | Web app (React + Next.js + Canvas 2D) |
| Budget | $0 — all free/open-source tools |
| Automation | n8n bidirectional (trigger + callback) |
| Input formats | Text prompt, .md, .pdf, image references |
| Content filter | No 18+, no harmful |
| Watermark | No |
| Privacy | User-only access |

## Components

### 1. Input Parser
- Accept text prompts directly
- Extract text from .md and .pdf files
- Accept image references for character consistency
- Validate against content filter before processing

### 2. Content Filter
- Block 18+ and harmful content
- Keyword-based + semantic filtering
- Detect prompts attempting to embed text/branding in video descriptions → redirect to text overlay layer

### 3. AI Planning Layer (GPT-4 / Claude)
- **Split** user prompt into 3–5 segment scripts (5–15s each)
- **Generate** per segment:
  - Video description — pure footage, camera, lighting, motion, NO text
  - Narration script for TTS
  - Title text + position
  - CTA text + position
  - Transition type (fade / wipe / slide)
- Output: JSON with timestamps and coordinates

### 4. Video Generation Layer (Segment Generator)
- **Primary:** Happy Horse via fal.ai — 15s max, 1080p+audio, 9:16 native, free credits
- **Fallbacks:** Luma Ray2 (10s, quality), Runway Gen-4.5 (10s, highest quality), Kling 3 (15s, character consistency)
- **Provider chain:** Happy Horse → Luma → Runway → Kling
- **Critical rule:** Prompts contain NO text — clean footage only

### 5. Audio Generation Layer (TTS Voiceover)
- **Primary:** Groq Orpheus "qrog" — fastest TTS, vocal directions ([cheerful], [whisper]), included with Groq API
- **Fallback 1:** ElevenLabs — 32+ voices, 10K chars/mo free
- **Fallback 2:** Fish Speech — open-source (Apache 2.0), 80+ languages, self-hosted
- Generate per-segment TTS from narration scripts

### 6. Music Generation Layer
- **Primary:** Suno / MiniMax Music — AI-generated, auto-matched to content mood
- **Fallback:** Royalty-free music library
- Auto-selected by content type (educational = calm, marketing = upbeat, tech = modern)

### 7. Canvas Editor (Frontend)
- **Base layer:** HTML5 `<video>` playing segments
- **Overlay layer:** Transparent `<canvas>` synced to `video.currentTime`
- **Text rendering:** Canvas 2D `fillText()` with web fonts
- **Drag-and-drop:** Pointer events for moving text boxes
- **Timeline scrubber:** Jump between segments, adjust start/end times
- **Transition selector:** Per-segment (fade / wipe / slide)
- **Preview mode:** 360p fast / 1080p final check
- **State:** JSON text-track model — same JSON feeds FFmpeg export

### 8. FFmpeg Export (Backend)
- **Segment concatenation:** `ffmpeg -f concat` with `xfade` transitions
- **Text overlay:** `drawtext` or ASS subtitles from JSON
- **Audio mixing:** `sidechaincompress` — TTS ducks BGM
  - `threshold=-24dB, ratio=6, attack=20ms, release=250ms`
- **Output:** 1080×1920 H.264 AAC MP4, `-crf 18, -movflags +faststart`

### 9. Publishing & Scheduling
- YouTube Data API v3 — upload + schedule publish
- n8n webhook endpoints (bidirectional)

### 10. Storage
- Cloudflare R2 for segments, audio, music, final MP4s
- PostgreSQL for metadata (users, segments, projects, edits)

### 11. Job Queue & Async Processing
- Redis + Celery — submit, poll, retry, fallback
- Per-segment progress tracking
- Email notification on completion/failure

### 12. Authentication & Rate Limiting
- Email/password + Google OAuth, JWT sessions
- Per-user rate limits within free API quotas
- API key auth for n8n/developer endpoints

## Implementation Phases

### Phase 1: Segment Generation + Basic Composition (Week 1–2)
- [x] 1. FastAPI backend scaffold
- [x] 2. Redis + Celery job queue
- [ ] 3. Email/password + Google OAuth auth
- [x] 4. Input parser (text, .md, .pdf)
- [x] 5. Content filter
- [x] 6. AI Planning layer (GPT-4 segment splitting)
- [ ] 7. **Happy Horse API via fal.ai** — generate 5–15s video segments
- [ ] 8. **Groq Orpheus TTS (qrog)** — per-segment voiceover
- [ ] 9. **Suno / MiniMax BGM** — auto-selected music
- [ ] 10. **FFmpeg composition** — concat + text overlay + audio mix
- [ ] 11. **Canvas editor scaffold** — React + Canvas, one segment
- [ ] 12. Segment model + API endpoint
- [x] 13. Job status polling

### Phase 2: Full Editor + Audio Mixing (Week 3)
1. Canvas drag-and-drop text positioning
2. Text styling (font, size, color, outline)
3. Timeline scrubber for multi-segment
4. Transition selector per segment
5. FFmpeg `xfade` transitions
6. FFmpeg `sidechaincompress` ducking
7. 360p low-res preview mode
8. User approval → 1080p export trigger

### Phase 3: Multi-Segment + Publishing (Week 4)
1. 3–5 segment timeline (30–75s total)
2. Segment reordering in editor
3. Regenerate individual segments
4. Final 1080p render
5. YouTube Data API v3 integration
6. n8n webhook endpoints

### Phase 4: Polish (Week 5)
1. API key auth for n8n/developer
2. Rate limiting + quota management
3. User library + prompt history UI
4. Cloud storage (R2) for all assets
5. Testing with real prompts
6. API documentation

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Job Queue | Redis + Celery |
| AI Planning | GPT-4 / Claude |
| Frontend | React + Next.js + HTML5 Canvas 2D |
| Video Preview | HTML5 `<video>` + Canvas overlay |
| Video Generation | Happy Horse (fal.ai), Luma Ray2, Runway Gen-4.5, Kling 3 |
| TTS | Groq Orpheus (qrog), ElevenLabs, Fish Speech |
| BGM | Suno / MiniMax, royalty-free library |
| Video Processing | FFmpeg: concat, xfade, drawtext, sidechaincompress |
| Database | PostgreSQL |
| Storage | Cloudflare R2 |
| Auth | Email/password + Google OAuth, JWT |
| Deployment | Railway / Render (free tier) |
| Automation | n8n bidirectional webhooks |
| Notifications | Email (Resend/SendGrid free tier) |

## Cost Strategy (Zero Budget)

- **Video:** Happy Horse free credits, fallback chain
- **TTS:** Groq Orpheus included, Fish Speech open-source
- **BGM:** Suno/MiniMax free tier
- **Editor:** Canvas 2D (browser, $0) + FFmpeg (open-source, $0)
- **Storage:** Cloudflare R2 generous free egress
- **YouTube API:** Free
- **Deployment:** Railway/Render free tier

## Security & Privacy

- User data never exposed externally
- API keys as env vars, never logged
- Content filtered before API submission
- Videos accessible only to creator
- No watermark
- Per-user API keys for n8n/developer
- JWT session management

## Open Research Items (Resolved)

| Item | Resolution |
|---|---|
| Copyright | Happy Horse, Luma, Runway, Kling: commercial rights. Fish Speech: Apache 2.0. |
| Misuse prevention | Content filter + safety checker + audit trail. C2PA watermarking deferred. |
| API portrait (9:16) | All 4 APIs support 1080×1920 natively. FFmpeg crop fallback. |
| Free tier limits | Happy Horse: free credits. Groq: included. Fish Speech: unlimited. Suno: free tier. |
| "qrog" TTS | Groq Orpheus — fastest TTS with vocal direction tags. English + Arabic. |
| Segment consistency | Reference images (1–9 via Happy Horse), Kling multi-shot, last-frame conditioning. |

---

*This document reflects the new segment-based layered architecture — replacing the old full-video generation plan.*