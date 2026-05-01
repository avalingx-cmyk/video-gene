# Project Plan: Video Creator

## Project Overview
Create a video from a user prompt (text input, with optional .md/.PDF file upload and image attachment). The system generates videos via third-party cloud APIs — no local GPU resources required.

## Goals
- Accept text prompts, .md/.PDF file uploads, and optional image attachments from the user.
- Generate videos ranging from 30 seconds to 5+ minutes in length.
- Target mobile portrait resolution: 1080x1920.
- Output format: MP4 only.
- Support audio generation alongside video (background music, voiceover).
- Specialize in educational, marketing, and technology videos for YouTube.
- Support both simple prompts and complex multi-action scenes.
- Allow basic video editing after generation (trimming, concatenation).
- Enable direct publishing to YouTube and social media with scheduled posting.
- Provide API access for developers (n8n automation and other integrations).
- Implement content filters (no 18+, no harmful content) and privacy measures.

## Architecture
1. **Input Module**: Receives user input — text prompt, optional .md/.PDF file upload, and optional image attachment for image-in-prompt support.
2. **Processing Module**:
   - Parses and enhances prompts with style, lighting, and camera descriptors.
   - Calls third-party cloud text-to-video APIs for video generation.
   - Calls third-party cloud audio APIs for background music/voiceover.
   - Includes content filtering before submission to generation APIs.
3. **Output Module**: Receives generated video from cloud API, applies post-processing (trimming, concatenation via FFmpeg), and delivers MP4 output.
4. **Publishing Module**: Direct upload to YouTube and social media platforms with scheduled posting support.
5. **Integration Module**: REST API and webhooks for n8n automation and other developer integrations.
6. **Safety & Ethics Module**: Content filtering (18+, harmful content), data privacy (user-only access), copyright research, and misuse prevention research.

## Technologies to Consider
- **Video Generation APIs**: Runway ML, Luma Dream Machine, Pika Labs, Kling AI, or similar cloud text-to-video services.
- **Audio APIs**: ElevenLabs (voiceover), Suno/Udio (music), or similar cloud audio generation services.
- **Backend**: Node.js (Express/Fastify) or Python (FastAPI) for API orchestration and webhook handling.
- **Frontend**: Simple web interface — React or vanilla JS with a clean, beginner-friendly UI.
- **Video Processing**: FFmpeg (server-side) for trimming, concatenation, and format conversion.
- **Database**: PostgreSQL for storing prompts, videos, user preferences, and scheduled publish jobs.
- **Storage**: Cloud storage (S3, R2, or Cloudflare) for video assets.
- **Deployment**: Cloud hosting (Vercel, Railway, Render, or similar) — zero local infrastructure.
- **Automation**: n8n webhooks and API endpoints for workflow integration.

## Updated Video API Research (2026)

### Best Free/Low-Cost Cloud APIs (No Local GPU Required)

| API | Free Tier | Rate Limit | Max Resolution | Audio | API Key Required | Notes |
|-----|-----------|------------|----------------|-------|-----------------|-------|
| **ZSky AI** | Unlimited (ad-supported) | 10 req/min | 1080p | Yes, included | No (free tier) | No credit card. cURL-only integration. 10s max duration. |
| **Happy Horse AI** | 10 free credits | — | 1080p | Yes, synchronized | No (free tier) | #1 ranked on Artificial Analysis. 15B param open-source model. Commercial license. |
| **Free.ai (CogVideoX)** | 2.5K tokens/day (no account), 5K (free account) | — | Varies | No | No | ~25-50 videos/day. Open-source CogVideoX on A100. Commercial use allowed. |
| **Veo 3.1 (veo3api.com)** | 100 credits/month (~20 gens) | 2 concurrent | High quality | Yes | Yes (free tier) | Google's model. Credits refresh monthly. Fast generation <5min. |
| **Luma Ray1.6** | Pay-per-use (credits) | High on paid | High quality | Yes | Yes | Leading quality. Camera control, image-to-video. |
| **Genbo.ai (Wan2.2)** | Paid only | High | 720p | No | Yes | Ultra-cheap: $0.005-$0.012 per video. Tencent's Wan2.2 model. |
| **LTX-2** | Paid only | High | 4K / 50fps | Yes, native | Yes | Fastest production-grade. Audio-to-video support. |

### Recommended Stack for This Project
1. **Primary (Free/Low-Cost)**: ZSky AI (truly free, 1080p+audio) + Happy Horse AI (highest quality, 10 free credits)
2. **Fallback**: Free.ai CogVideoX (token-based, no card)
3. **Paid Scaling**: Veo 3.1 (100 free credits/month) or Luma Ray1.6 (best quality)
4. **Ultra-low-cost option**: Genbo.ai Wan2.2 at $0.005/video

### Key Findings
- **ZSky AI** is the only truly free cloud API with no credit card, no API key for free tier, and 1080p+audio output
- **Happy Horse AI** (HappyHorse 1.0) is open-source, #1 ranked, and offers 10 free credits to start
- **Free.ai** uses CogVideoX (Apache 2.0 license) with ~25-50 free videos/day
- All leading APIs now support **native audio synchronization** (ZSky, Happy Horse, Veo 3.1, LTX-2)
- **No local GPU needed** — all options are cloud-hosted REST APIs

## Milestones
1. Research and select appropriate third-party cloud APIs for text-to-video and audio generation.
2. Set up development environment and cloud hosting.
3. Implement core generation pipeline (prompt processing → cloud API calls → MP4 output).
4. Build simple web interface for prompt input and video download.
5. Implement video editing features (trimming, concatenation).
6. Implement YouTube/social media publishing with scheduling.
7. Implement n8n/webhook API integrations.
8. Add content filtering and safety features.
9. Test with various prompts and refine quality.
10. Deploy and iterate.

## Deployment Considerations
- Target deployment: Web app only (no desktop or local deployment).
- Usage patterns: Support both occasional users and heavy usage via n8n automation.
- Latency: Cloud API dependent; implement job queuing and status polling for long generations.
- Budget: $0 for compute — entirely third-party cloud APIs. Pay-per-use model for API calls.
- Connectivity: Online only; no offline support.

## User Experience
- Target audience: Kids, parents, social media users, marketing professionals, YouTube creators, tech users, problem solvers, and knowledge sharers.
- Technical level: Beginners learning new tech or solving issues — simple interface only, no advanced controls.
- Output format: MP4 only.
- Post-generation editing: Trimming and concatenation within the app.
- Input: Text prompt, .md file upload, .PDF file upload, optional image attachment in prompt.

## Operations & Reliability
- **Job queuing**: Video generation APIs are async with long wait times; use job queue with status polling and webhook callbacks.
- **Retry strategy**: Automatic retry on API failure with exponential backoff; fallback to next provider in router chain.
- **Error notifications**: In-app status updates; email notification on completion or failure for long jobs.
- **Rate limiting**: Per-user rate limits to stay within free-tier API quotas; queue excess requests.

## User Management
- **Authentication**: Simple email/password or OAuth (Google); lightweight for now.
- **Multi-user**: Each user has their own video library, prompts, and scheduled publishes.
- **User roles**: Single role for now (no admin/creator distinction yet).

## Audio Details
- **Voiceover languages**: English only for now.
- **Voice style**: Natural/conversational for educational; professional for marketing/tech.
- **Background music style**: Matches video content type — auto-determined by prompt enhancer; user does not select manually.
- **User audio upload**: Not supported — audio is generated only.

## n8n Integration Details
- **Trigger direction**: Bidirectional — n8n can trigger video generation via webhook, and completed videos can trigger n8n workflows.
- **Payload format**: JSON with prompt, settings, and callback URL for async completion.
- **Authentication for API**: API key per user for developer/n8n access.

## API Research Items
- **Copyright**: Do generated videos from AI models have clear usage rights? Do any APIs claim ownership?
- **Misuse prevention**: What detection methods work for deepfake-style content generation?
- **API portrait support**: Which video generation APIs actually support 1080x1920 output natively vs. requiring post-crop?

## Safety and Ethics
- Content filtering: Block all 18+ and harmful content.
- Copyright: Research needed on training data and generated content rights.
- Watermarking: Disabled for now.
- Data privacy: User-only access; no exposure of prompts or generated content.
- Misuse prevention: Research needed on prevention strategies.
