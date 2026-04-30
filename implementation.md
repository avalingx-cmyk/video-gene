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

## Implementation Steps

### Phase 1: Foundation (Week 1-2)
1. Set up FastAPI backend project structure
2. Implement input parser (text, .md, .pdf extraction)
3. Build content filter module
4. Implement prompt enhancer for educational/marketing/tech styles
5. Integrate ONE video generation API (start with Replicate for flexibility)
6. Basic web UI — simple prompt input, file upload, video display
7. FFmpeg integration for MP4 output at 1080x1920

### Phase 2: Audio & Post-Processing (Week 3)
1. Integrate text-to-speech API for voiceover
2. Add background music generation/selection
3. Implement video trimming and concatenation
4. Audio-video mixing pipeline

### Phase 3: Integrations (Week 4)
1. YouTube API integration with scheduling
2. n8n webhook endpoints for automation
3. Additional video API integrations (Runway, Pika, Luma)
4. API router with fallback chain

### Phase 4: Polish & Launch (Week 5)
1. Cloud storage setup (S3/R2)
2. PostgreSQL metadata storage
3. Simple web interface refinement
4. Testing with real prompts across content types
5. API documentation for n8n and developer access

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Frontend | Svelte (simple, lightweight) or Next.js |
| Video APIs | Replicate, Runway ML, Pika, Luma (3rd party) |
| Audio APIs | ElevenLabs (TTS), royalty-free music library |
| Video Processing | FFmpeg + ffmpeg-python |
| Database | PostgreSQL |
| Storage | S3 or Cloudflare R2 |
| PDF Parsing | PyPDF2 or pdfplumber |
| MD Parsing | markdown library |
| Deployment | Railway / Render / Fly.io (free tier) |
| Automation | n8n webhook endpoints |

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
