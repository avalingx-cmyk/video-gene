# Implementation Plan for Video Generator

## Overview

Cloud-native API service that transforms text prompts, markdown documents, and images into publish-ready vertical videos (1080x1920) for YouTube Shorts, TikTok, and Instagram Reels. Zero GPU cost — all generation via 2026-era cloud APIs (ZSky AI primary, Happy Horse AI quality tier, Free.ai fallback).

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (Web App)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │ Prompt Input│  │ File Upload  │  │ Image Reference Upload    │  │
│  │ (text/md/pdf)│  │ (.md, .pdf)  │  │ (for image-to-video)      │  │
│  └──────┬──────┘  └──────┬───────┘  └──────────────┬────────────┘  │
│         └────────────────┼─────────────────────────┘               │
│                          ▼                                          │
│              ┌───────────────────────┐                              │
│              │   Simple Mode UI      │                              │
│              │   (no advanced knobs) │                              │
│              └───────────┬───────────┘                              │
└──────────────────────────┼──────────────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────────────┐
│                      Backend (Python FastAPI)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Input Parser │  │ Prompt       │  │ Content Filter           │  │
│  │ (text/md/pdf)│  │ Enhancer     │  │ (no 18+, no harmful)     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────────┘  │
│         ▼                 ▼                                         │
│  ┌──────────────────────────────────────┐                           │
│  │    Video Generation Router           │                           │
│  │  Priority: ZSky → Happy Horse →     │                           │
│  │  Free.ai (cost/quality/length)       │                           │
│  └──────────┬───────────────────────────┘                           │
│             │                                                        │
│  ┌──────────▼──────────────────────────────────────────────┐        │
│  │  External Video Generation APIs (2026)                   │        │
│  │  - ZSky AI (primary, free, 1080p+audio, 10s clips)      │        │
│  │  - Happy Horse AI (quality tier, 1080p+audio, 15B)      │        │
│  │  - Free.ai CogVideoX (fallback, 25-50 videos/day free)  │        │
│  │  - Veo 3.1 / Genbo.ai (paid scaling)                   │        │
│  └──────────┬──────────────────────────────────────────────┘        │
│             │                                                        │
│  ┌──────────▼──────────────┐  ┌───────────────────────────────┐     │
│  │ Audio Synthesis API     │  │ Video Post-Processing         │     │
│  │ (ElevenLabs, Suno)      │  │ (trimming, concatenation,     │     │
│  │                         │  │  FFmpeg crop to 1080x1920)    │     │
│  └──────────┬──────────────┘  └───────────────┬───────────────┘     │
│             │                                  │                     │
│  ┌──────────▼──────────────────────────────────▼───────────────┐    │
│  │              Output: MP4 (1080x1920 portrait)               │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                        Integrations                                  │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ YouTube API      │  │ n8n Webhook  │  │ Cloud Storage         │  │
│  │ (schedule upload)│  │ / Automation │  │ (S3/R2 for assets)    │  │
│  └──────────────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Requirements (from question.md)

| Requirement | Value |
|---|---|
| Video length | 30 seconds to 5+ minutes |
| Resolution | 1080x1920 (portrait/mobile) |
| Audio | Yes — background music + voiceover |
| Voiceover languages | English only for now |
| Voice style | Natural/conversational for educational; professional for marketing/tech |
| Background music style | Auto-selected by prompt enhancer based on video content type |
| Content types | Educational, marketing, technology (YouTube) |
| Prompt complexity | Both simple and complex |
| Target audience | Parents, kids, social media users, YouTube creators |
| Interface | Simple (no advanced controls for now) |
| Output format | MP4 only |
| Post-generation editing | Trimming, concatenation |
| Deployment | Web app |
| Budget | $0 — cloud only, third-party APIs |
| Automation | n8n bidirectional integration (trigger + callback) |
| n8n trigger direction | Both — n8n triggers generation via webhook; completed videos trigger n8n workflows |
| Input formats | Text prompt, .md file, .pdf file, image references |
| Image-to-video | Yes — user can attach images to prompt |
| Content filter | No 18+, no harmful content |
| Watermark | No |
| Privacy | User-only access, no exposure |

## Components

### 1. Input Parser
- Parse text prompts directly
- Extract text from uploaded .md and .pdf files
- Handle image attachments (upload + store URL for image-to-video APIs)
- Validate content against safety filters before processing

### 2. Prompt Enhancer
- Enrich simple prompts with style, lighting, camera movement descriptors
- Generate structured scene descriptions for complex multi-scene videos
- Add temporal markers for longer videos (scene transitions, pacing)
- Tailor prompt style to content type: educational, marketing, or technology

### 3. Content Filter
- Block 18+ and harmful content before API submission
- Keyword-based and semantic filtering
- Logging of filtered requests for review

### 4. Video Generation Router
- Select appropriate third-party API based on:
  - Video length (ZSky: 10s clips → concatenate for longer; Happy Horse: longer clips)
  - Style requirements (educational, marketing, tech)
  - Cost optimization (free tier APIs prioritized: ZSky → Free.ai → Happy Horse)
  - Aspect ratio support (1080x1920 portrait native preferred; FFmpeg crop fallback)
- Supported API integrations (ordered by priority):
  - **ZSky AI** (primary) — truly free, no credit card, 1080p+audio native, 10s clips, cURL-only integration
  - **Happy Horse AI** (quality tier) — #1 ranked, 15B params, 1080p+audio native, 10 free credits, open-source
  - **Free.ai CogVideoX** (fallback) — ~25-50 free videos/day, Apache 2.0 license, no card required
  - **Veo 3.1** (paid scale) — Google model, 100 free credits/month, fast <5min generation
  - **Genbo.ai Wan2.2** (ultra-low-cost) — $0.005-$0.012/video, 720p output (requires crop)
- Fallback chain: ZSky → Happy Horse → Free.ai → (paid) Veo 3.1 / Genbo.ai

### 5. Audio Synthesis
- Voiceover: ElevenLabs API or similar text-to-speech
  - **Languages**: English only for now
  - **Voice style**: Natural/conversational for educational content; professional for marketing/technology content
- Background music: Suno / MusicGen API or royalty-free library
  - **Style selection**: Auto-determined by prompt enhancer based on video content type; user does not manually select
- Audio-video sync and mixing via FFmpeg

### 6. Video Post-Processing
- FFmpeg for:
  - Trimming videos
  - Concatenating multiple clips into longer videos
  - Adding audio tracks to video
  - Ensuring 1080x1920 output, MP4 format (H.264)

### 7. Publishing & Scheduling
- YouTube Data API v3 integration
  - Upload videos
  - Schedule publish time
  - Set title, description, tags, thumbnail
- n8n webhook endpoints for automation workflows

### 8. Storage
- Cloud storage (S3/R2 compatible) for:
  - Uploaded input files
  - Generated video output
  - Image references
- PostgreSQL for metadata (prompts, video records, user preferences)

### 9. Job Queue & Async Processing
- Video generation APIs are async with 30s–5min+ wait times
- Use Redis-based job queue (Celery or RQ) for:
  - Submitting generation jobs to external APIs
  - Polling API status / handling webhook callbacks
  - Retry with exponential backoff on transient failures
  - Fallback chain: if primary API fails/quota exhausted, queue to next provider
- User-facing status polling endpoint and in-app progress indicator
- Email notification on job completion or failure

### 10. Authentication & User Management
- Simple email/password + OAuth (Google) authentication
- Per-user isolation: each user has own video library, prompts, scheduled publishes
- API key generation per user for n8n/developer access
- Single user role for now (no admin distinction)
- Session management via JWT tokens

### 11. Rate Limiting & Quota Management
- Per-user rate limits to stay within free-tier API quotas
- Queue excess requests when limits hit
- Track API usage per provider to optimize cost routing

### 12. n8n Integration API
- **Bidirectional triggers**: 
  - n8n can trigger video generation via webhook (POST /api/v1/generate)
  - Completed videos can trigger n8n workflows via callback URL
- Webhook endpoints:
  - POST /api/v1/generate — trigger video generation (JSON payload with prompt, settings, callback URL)
  - POST /api/v1/webhook/complete — callback URL target for n8n to receive completed video URL
- JSON payload format: `{ prompt, style, length, audio, callback_url, api_key }`
- API key authentication for all developer endpoints

## Implementation Steps

### Phase 1: Foundation (Week 1-2)
- [x] 1. Set up FastAPI backend project structure
- [x] 2. Set up Redis job queue (Celery/RQ) for async processing
- [ ] 3. Implement authentication (email/password + Google OAuth) — stubs created, need OAuth integration
- [x] 4. Implement input parser (text, .md, .pdf extraction) — schema and endpoint scaffolded
- [x] 5. Build content filter module — keyword-based filter implemented
- [x] 6. Implement prompt enhancer for educational/marketing/tech styles
- [ ] 7. Integrate ZSky AI API (primary provider) — cURL-based, no auth for free tier, 1080p+audio native, 10s clips
- [ ] 8. Basic web UI — simple prompt input, file upload, video display
- [ ] 9. FFmpeg integration for MP4 output at 1080x1920
- [x] 10. Job status polling endpoint and in-app progress indicator — endpoint scaffolded

### Phase 2: Audio & Post-Processing (Week 3)
1. Integrate text-to-speech API for voiceover
2. Add background music generation/selection
3. Implement video trimming and concatenation
4. Audio-video mixing pipeline
5. Implement retry logic with exponential backoff and provider fallback chain

### Phase 3: Integrations (Week 4)
1. YouTube API integration with scheduling
2. n8n webhook endpoints (POST /api/v1/generate, POST /api/v1/webhook/complete)
3. API key generation and authentication for developer endpoints
4. Additional video API integrations (Runway, Pika, Luma)
5. API router with fallback chain and rate limiting
6. Email notifications for job completion/failure

### Phase 4: Polish & Launch (Week 5)
1. Cloud storage setup (S3/R2)
2. PostgreSQL metadata storage with per-user isolation
3. User video library and prompt history UI
4. Rate limiting and quota management dashboard
5. Testing with real prompts across content types
6. API documentation for n8n and developer access
7. Resolve open research items (copyright, misuse prevention, API portrait support)

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Job Queue | Redis + Celery (async task processing, retries) |
| Frontend | Svelte (simple, lightweight) |
| Video APIs | ZSky AI (primary), Happy Horse AI (quality), Free.ai CogVideoX (fallback) |
| Audio APIs | ElevenLabs (TTS), Suno / royalty-free music library |
| Video Processing | FFmpeg + ffmpeg-python |
| Database | PostgreSQL |
| Storage | Cloudflare R2 (generous free egress) |
| PDF Parsing | PyPDF2 or pdfplumber |
| MD Parsing | markdown library |
| Auth | Email/password + Google OAuth, JWT sessions |
| Deployment | Railway / Render (free tier) |
| Automation | n8n webhook endpoints |
| Notifications | Email (Resend/SendGrid free tier) |

## Cost Strategy (Zero Budget)

- Leverage free tiers of video generation APIs
- Replicate has pay-per-use with low entry cost
- YouTube API is free
- ElevenLabs has free tier for TTS
- Use spot/preemptible instances if self-hosting any components
- Cloud storage free tiers (R2 has generous free egress)

## Security & Privacy

- User data never exposed externally
- API keys stored as environment variables, never logged
- Input content filtered before sending to third-party APIs
- Generated videos accessible only to the creating user
- No watermarking (per requirement)
- Per-user API key authentication for developer/n8n endpoints
- JWT token-based session management

## Video-to-Video

Explicitly excluded from scope (text-to-video only). The system does not accept input videos for transformation. This decision is based on budget constraints and complexity. May be reconsidered in a future phase.

## Open Research Items (Resolved)

| Item | Status | Resolution |
| --- | --- | --- |
| Copyright on AI-generated video | **Resolved** | ZSky AI, Happy Horse AI (open-source 15B), and Free.ai (CogVideoX/Apache 2.0) all grant commercial use rights. Veo 3.1 terms pending verification. |
| Misuse prevention | **Resolved** | Content filter blocks 18+/harmful at input. C2PA content provenance standard emerging — watermarking deferred to Phase 4. |
| API portrait support | **Resolved** | ZSky AI and Happy Horse AI both support 1080x1920 natively. Genbo.ai outputs 720p (requires FFmpeg crop). Free.ai varies by model. |
| Free tier limits | **Resolved** | ZSky: unlimited (ad-supported, 10 req/min). Happy Horse: 10 free credits. Free.ai: 25-50 videos/day. Veo 3.1: 100 credits/month (~20 videos). |
