# Project Plan: Video Generator

## Improved Concept (May 2026)

**Video Generator** is a cloud-native API service that transforms text prompts, markdown documents, and images into publish-ready vertical videos (1080x1920) for YouTube Shorts, TikTok, and Instagram Reels. The system targets the creator economy: educators, marketers, and tech creators who need fast, low-cost video content without learning video editing tools.

**Core value proposition**: Zero-GPU, zero-editing video creation. User provides a prompt or document; the system returns a ready-to-publish MP4 with synchronized audio in under 5 minutes.

## Strategic API Selection (2026 Research-Based)

| Priority | API | Free Tier | 1080x1920 Native | Audio Sync | Integration Effort |
|----------|-----|----------|------------------|------------|---------------------|
| **1 (Primary)** | **ZSky AI** | Unlimited (ad-supported) | Yes | Yes, native | Low — cURL-only, no API key |
| **2 (Quality)** | **Happy Horse AI** | 10 free credits | Yes | Yes, native | Low — REST, no key for free tier |
| **3 (Scale)** | **Veo 3.1** | 100 credits/month (~20 videos) | Yes | Yes, native | Medium — webhooks + SSE |
| **4 (Budget)** | **Genbo.ai Wan2.2** | Paid: $0.005-$0.012/video | 720p (crop to 1080x1920) | No | Low — REST API |
| **5 (Fallback)** | **Free.ai CogVideoX** | 25-50 videos/day | Varies | No | Medium — token-based |

**Key decision**: Start with ZSky AI as primary (truly free, no card, native 1080x1920+audio). Use Happy Horse AI for quality-sensitive content. Fall back to Free.ai when ZSky quota or content filters block a request.

## Architecture (Simplified, Actionable)

```
User Input (text/md/pdf/image)
        │
        ▼
┌─────────────────────┐
│  FastAPI Backend    │
│  ┌───────────────┐  │
│  │ Content Filter│  │  ← Keyword + semantic blocking
│  └───────┬───────┘  │
│  ┌───────▼───────┐  │
│  │ Prompt        │  │  ← Enrich with style/lighting/camera descriptors
│  │ Enhancer      │  │
│  └───────┬───────┘  │
│  ┌───────▼───────┐  │
│  │ Provider      │  │  ← ZSky → Happy Horse → Free.ai
│  │ Router        │  │
│  └───────┬───────┘  │
│  ┌───────▼───────┐  │
│  │ FFmpeg        │  │  ← Ensure 1080x1920, add audio if needed
│  │ Post-Process  │  │
│  └───────┬───────┘  │
└──────────┼──────────┘
           │
           ▼
    MP4 (1080x1920) → Cloud Storage → Callback/Webhook
           │
           └──→ YouTube API (scheduled publish)
           └──→ n8n webhook (automation trigger)
```

## Implementation Phases

### Phase 1: Working Prototype (Current Sprint)
**Goal**: Generate a video from a text prompt using ZSky AI and return an MP4.

- [x] FastAPI backend scaffold
- [x] Redis + Celery job queue
- [x] Content filter (keyword-based)
- [x] Prompt enhancer (educational/marketing/tech styles)
- [ ] **Integrate ZSky AI API** (cURL-based, no auth for free tier)
- [ ] FFmpeg post-processing (ensure 1080x1920 output)
- [ ] Basic web UI (prompt input → video output)
- [ ] Job status polling endpoint

### Phase 2: Multi-Provider + Audio (Next Sprint)
- [ ] Happy Horse AI integration (quality tier)
- [ ] Free.ai CogVideoX integration (fallback tier)
- [ ] Provider router with cost/quality selection logic
- [ ] ElevenLabs TTS for voiceover (English only)
- [ ] Background music via royalty-free library or Suno API
- [ ] Audio-video mixing via FFmpeg

### Phase 3: Publishing + Automation (Following Sprint)
- [ ] YouTube Data API v3 (upload + scheduled publish)
- [ ] n8n webhook: `POST /api/v1/generate` (trigger from n8n)
- [ ] n8n callback: completed video URL → trigger n8n workflow
- [ ] API key auth for developer endpoints
- [ ] Per-user rate limiting (stay within free-tier quotas)

### Phase 4: Polish + Launch
- [ ] Cloud storage (R2/S3) for video assets
- [ ] PostgreSQL metadata (user libraries, prompt history)
- [ ] User auth (email/password + Google OAuth)
- [ ] Testing with real prompts across all content types
- [ ] Resolve copyright/misuse prevention research items

## Resolved Research Items

| Item | Resolution |
|------|------------|
| **Copyright** | ZSky AI, Happy Horse AI, and Free.ai (CogVideoX/Apache 2.0) all grant commercial use rights to generated content. Veo 3.1 terms pending verification. |
| **Misuse prevention** | Content filter blocks 18+/harmful at input. C2PA content provenance standard emerging — defer watermarking decision to Phase 4. |
| **API portrait support** | ZSky AI and Happy Horse AI both support 1080x1920 natively. Genbo.ai outputs 720p — requires post-crop. Free.ai varies by model. |

## Technology Stack (Confirmed)

| Layer | Choice | Reason |
|-------|--------|--------|
| Backend | Python 3.11+ / FastAPI | Already scaffolded, async support |
| Job Queue | Redis + Celery | Already scaffolded, retry + backoff |
| Frontend | Svelte (lightweight) | Simple UI, fast delivery |
| Video APIs | ZSky AI → Happy Horse → Free.ai | 2026 research-based, free-tier first |
| Audio APIs | ElevenLabs (TTS) + royalty-free music | Free tiers available |
| Video Processing | FFmpeg + ffmpeg-python | Industry standard, already planned |
| Database | PostgreSQL | User data, video metadata |
| Storage | Cloudflare R2 | Generous free egress |
| Auth | JWT + Google OAuth | Simple, already scaffolded |
| Deployment | Railway / Render | Free tier, zero GPU cost |

## Constraints & Decisions

- **Budget**: $0 compute cost — all generation via third-party APIs with free tiers
- **Video length**: 30 seconds to 5+ minutes (provider-dependent; ZSky limited to 10s clips — concatenate for longer)
- **Resolution**: 1080x1920 native when possible; FFmpeg crop as fallback
- **Audio**: Native when API provides it; mixed via FFmpeg when separate
- **Content**: Educational, marketing, technology only — no 18+, no harmful content
- **Editing**: Trimming + concatenation only (no advanced timeline editing)
- **Watermark**: Disabled per requirements
- **Video-to-video**: Explicitly out of scope (text-to-video only)
