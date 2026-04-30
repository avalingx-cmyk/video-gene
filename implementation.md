# Implementation Plan for Video Generator

## Overview

Cloud-based video generation platform that creates videos from text prompts, markdown files, PDFs, and image references. Targets educational, marketing, and technology content for YouTube. Zero self-hosted GPU cost — all generation via third-party APIs.

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
│  │  (selects 3rd-party API by cost/     │                           │
│  │   quality/length requirements)       │                           │
│  └──────────┬───────────────────────────┘                           │
│             │                                                        │
│  ┌──────────▼──────────────────────────────────────────────┐        │
│  │  External Video Generation APIs                         │        │
│  │  - Runway ML / Pika / Luma / Replicate / OpenAI Sora   │        │
│  │  - Selection based on video length & style              │        │
│  └──────────┬──────────────────────────────────────────────┘        │
│             │                                                        │
│  ┌──────────▼──────────────┐  ┌───────────────────────────────┐     │
│  │ Audio Synthesis API     │  │ Video Post-Processing         │     │
│  │ (ElevenLabs, MusicGen)  │  │ (trimming, concatenation)     │     │
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
| Content types | Educational, marketing, technology (YouTube) |
| Prompt complexity | Both simple and complex |
| Target audience | Parents, kids, social media users, YouTube creators |
| Interface | Simple (no advanced controls for now) |
| Output format | MP4 only |
| Post-generation editing | Trimming, concatenation |
| Deployment | Web app |
| Budget | $0 — cloud only, third-party APIs |
| Automation | n8n integration |
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
  - Video length (short clips vs. 5+ minute videos)
  - Style requirements (educational, marketing, tech)
  - Cost optimization (free tier APIs prioritized)
  - Aspect ratio support (1080x1920 portrait)
- Supported API integrations:
  - **Runway ML** — high quality, good for marketing content
  - **Pika Labs** — versatile, good prompt following
  - **Luma Dream Machine** — longer video support
  - **Replicate** — marketplace with multiple model options
  - **OpenAI Sora** (when available) — longest video support
- Fallback chain: if primary API fails or quota exhausted, try next

### 5. Audio Synthesis
- Voiceover: ElevenLabs API or similar text-to-speech
- Background music: Suno / MusicGen API or royalty-free library
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
- [ ] 7. Integrate ONE video generation API (start with Replicate for flexibility) — router scaffolded, provider calls TODO
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
| Frontend | Svelte (simple, lightweight) or Next.js |
| Video APIs | Replicate, Runway ML, Pika, Luma (3rd party) |
| Audio APIs | ElevenLabs (TTS), royalty-free music library |
| Video Processing | FFmpeg + ffmpeg-python |
| Database | PostgreSQL |
| Storage | S3 or Cloudflare R2 |
| PDF Parsing | PyPDF2 or pdfplumber |
| MD Parsing | markdown library |
| Auth | Email/password + Google OAuth, JWT sessions |
| Deployment | Railway / Render / Fly.io (free tier) |
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

## Open Research Items

| Item | Status | Notes |
|---|---|---|
| Copyright on AI-generated video | Unresolved | Need to verify ToS of each video API — do they claim ownership? Can generated content be used commercially? |
| Misuse prevention | Unresolved | Need to evaluate watermarking options, content provenance standards (C2PA), and detection methods |
| API portrait mode support | Unresolved | Verify which APIs natively support 1080x1920 vs. requiring post-crop (adds compute cost) |
| Free tier limits | Unresolved | Document exact free-tier quotas per API to plan rate limiting accurately |
