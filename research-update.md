# Research Update: Text-to-Video Generation

## Current State of Text-to-Video Technology (as of 2026)

### Leading Open-Source Models
1. **Stable Video Diffusion (SVD)** - Stability AI
   - Generates 2-4 second videos at 576x1024 resolution
   - Based on Stable Diffusion image model
   - Available via Hugging Face diffusers

2. **ModelScopeT2V** - Alibaba DAMO Academy
   - Supports text-to-video generation
   - Various model sizes available
   - Good for short video clips

3. **VideoCrafter2** - Tencent AI Lab
   - High-quality video generation
   - Supports longer sequences
   - Advanced temporal consistency

4. **AnimateDiff** - Guided diffusion for video
   - Adds motion to existing text-to-image models
   - Works with Stable Diffusion checkpoints
   - Efficient inference

5. **PIKA Labs** (open-source alternatives)
   - Various community implementations
   - Good prompt understanding

### Key Techniques for Temporal Consistency
- **Cross-frame Attention**: Ensuring consistent objects across frames
- **Motion Magnitude Control**: Regulating movement intensity
- **Latent Space Optimization**: Operating in compressed video latent space
- **Post-processing**: Optical flow-based frame interpolation

### Prompt Engineering for Video
- Temporal descriptors: "slowly panning", "quick zoom", "time-lapse"
- Style modifiers: "cinematic", "anime style", "photorealistic"
- Camera movements: "tracking shot", "dolly in", "aerial view"
- Lighting: "golden hour", "neon lights", "soft shadows"

### Hardware Requirements
- Minimum: 8GB GPU VRAM for short clips
- Recommended: 12-24GB GPU VRAM for better quality/length
- For production: A100 (40GB) or RTX 4090 (24GB)

### Integration Approaches
1. **API-based**: Use Replicate, Hugging Face Inference API
2. **Self-hosted**: Deploy models on GPU instances
3. **Hybrid**: Local preprocessing, cloud generation

### Safety and Ethical Considerations
- Content filtering for harmful generations
- Copyright awareness for training data
- Watermarking AI-generated content
- Disclosure of AI involvement

## Recommended Approach for Video Creator Project

Given the project scope and timeline, I recommend a phased approach:

### Phase1: Prototype (Weeks 1-2)
- Use Stable Diffusion XL for keyframe generation
- Implement RIFE frame interpolation
- Generate 2-3 second videos at 24 FPS
- Simple web interface for prompt input

### Phase2: Enhancement (Weeks 3-4)
- Integrate Stable Video Diffusion for direct video generation
- Add style control via LoRAs
- Implement prompt enhancement pipeline
- Better UI with preview and controls

### Phase3: Optimization (Week 5)
- Model quantization for faster inference
- Batch processing capabilities
- Cloud deployment preparation
- Comprehensive testing

## Resources
- Hugging Face Hub: https://huggingface.co/models?library=diffusers
- Stable Video Diffusion: https://huggingface.co/stabilityai/stable-video-diffusion-img2vid
- AnimateDiff: https://github.com/guoyww/AnimateDiff
- VideoCrafter2: https://github.com/AILab-CVC/VideoCrafter2
- RIFE: https://github.com/hzwer/arXiv2020-RIFE

---

## Updated Cloud API Research (May 2026)

### Best Free/Low-Cost Cloud Video APIs (No Local GPU Required)

| API | Free Tier | Rate Limit | Max Resolution | Audio | API Key | Notes |
|-----|-----------|------------|----------------|-------|---------|-------|
| **ZSky AI** | Unlimited (ad-supported) | 10 req/min | 1080p | Yes | No | Truly free. cURL-only. 10s max. No card. |
| **Happy Horse AI** | 10 free credits | — | 1080p | Yes | No | #1 on Artificial Analysis. 15B params. Open-source. |
| **Free.ai (CogVideoX)** | 2.5K-5K tokens/day | — | Varies | No | No | ~25-50 videos/day. Apache 2.0 license. |
| **Veo 3.1** | 100 credits/month | 2 concurrent | High | Yes | Yes | Google model. Credits refresh monthly. |
| **Luma Ray1.6** | Pay-per-use | High | High | Yes | Yes | Leading quality. Camera control. |
| **Genbo.ai (Wan2.2)** | Paid | High | 720p | No | Yes | $0.005-$0.012/video. Tencent model. |
| **LTX-2** | Paid | High | 4K/50fps | Yes | Yes | Fastest. Audio-to-video support. |

### Best Recommendation for This Project

**Top Choice: ZSky AI**
- Completely free, no credit card required
- 1080p + synchronized audio
- REST API (single cURL command)
- Unlimited daily generation (ad-supported)
- No API key needed for free tier

**Runner-up: Happy Horse AI (HappyHorse 1.0)**
- #1 ranked text-to-video model (Artificial Analysis)
- 15B parameter open-source transformer
- 1080p with audio sync
- 10 free credits to start
- Commercial license included

**Budget Option: Genbo.ai Wan2.2**
- Ultra-low-cost at $0.005-$0.012 per video
- 720p output
- High-speed generation with TurboDiffusion

### Key Findings
- **ZSky AI** is the only truly free cloud API with no credit card, no API key for free tier, and 1080p+audio output
- **Happy Horse AI** is open-source, #1 ranked, and offers 10 free credits to start
- **Free.ai** uses CogVideoX (Apache 2.0) with ~25-50 free videos/day
- All leading APIs now support **native audio synchronization** (ZSky, Happy Horse, Veo 3.1, LTX-2)
- **No local GPU needed** — all options are cloud-hosted REST APIs
- For n8n integration: ZSky AI (simple cURL), Veo 3.1 (webhooks + SSE), Luma (REST + webhooks)

### Answer to DIN-60: Best Free AI Video Model
**Best free cloud API: ZSky AI** — truly free (no card), 1080p+audio, REST API, unlimited daily generation.
**Best quality free option: Happy Horse AI** — #1 ranked, 15B params, 10 free credits, open-source.
