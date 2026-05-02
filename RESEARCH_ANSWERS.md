# Research Answers: Open Questions from question.md

## Question 43: Copyright — Do generated videos have clear usage rights?

### Answer: YES — All major APIs grant full commercial rights

| API | Copyright Status | Source |
|-----|-----------------|--------|
| **Happy Horse (fal.ai)** | ✅ **Full commercial rights on all outputs** | fal.ai Terms of Service |
| **Luma Ray2** | ✅ Commercial use permitted | Luma Labs Terms |
| **Runway Gen-4.5** | ✅ Full commercial rights | Runway Terms |
| **Kling 3** | ✅ Commercial use permitted | Kling Terms |
| **Fish Speech (TTS)** | ✅ Apache 2.0 license (open-source) | GitHub repository |
| **ElevenLabs (TTS)** | ✅ Commercial use with paid plan | ElevenLabs Terms |

**Key finding**: None of the APIs claim ownership of generated content. Users retain full rights to use, distribute, and monetize outputs.

**User responsibility**: Ensure input prompts don't violate third-party copyrights (e.g., " recreate the exact opening scene of Star Wars" would be problematic). The content filter should catch obvious trademark violations.

**Recommendation**: Add a terms acceptance checkbox in the UI before first generation, stating "I confirm I have rights to use the input content and understand generated videos are my responsibility."

---

## Question 44: Misuse Prevention — Deepfake-style content detection?

### Answer: Partial solutions exist — full prevention requires multi-layer approach

**Current capabilities:**
1. **Content filter** (already implemented): Keyword-based + semantic filtering blocks 18+/harmful content at input stage
2. **API-level safety checkers**: Happy Horse has `enable_safety_checker` flag that moderates both input and output
3. **C2PA content provenance**: Emerging standard (2026) for embedding metadata into media files to trace AI-generated content

**Limitations:**
- No 100% reliable deepfake detection exists yet
- Audio deepfakes (voice cloning) are harder to detect than video
- Per-user API keys provide accountability but not prevention

**Recommended multi-layer approach:**
1. **Input filtering**: Block prompts requesting impersonation of real people without consent
2. **Output watermarking**: Optional C2PA metadata embedding (deferred to Phase 4)
3. **Usage tracking**: Per-user API keys + rate limiting = audit trail
4. **Reporting mechanism**: Allow users to flag misuse
5. **Human review**: For high-volume users or suspicious patterns

**Conclusion**: The content filter + API safety checkers + audit trail provides reasonable protection for an MVP. Advanced deepfake detection can be added in Phase 4.

---

## Question 45: API Portrait Support — Which APIs support 1080x1920 natively?

### Answer: 4/4 major APIs support 9:16 natively

| API | Native 9:16 Support | Max Duration | Resolution | Audio |
|-----|---------------------|--------------|------------|-------|
| **Happy Horse (fal.ai)** | ✅ Yes (`aspect_ratio: "9:16"`) | 15s | 1080p | Native |
| **Luma Ray2** | ✅ Yes | 10s | 1080p | Native |
| **Runway Gen-4.5** | ✅ Yes | 10s | 1080p | Native |
| **Kling 3** | ✅ Yes | 15s | 1080p | Native |

**No post-crop needed** for any of these APIs when targeting 9:16 portrait format.

**Pricing** (for budget analysis):
- Happy Horse 1080p: **$0.28/second** (a 10s clip = $2.80)
- Happy Horse 720p: **$0.14/second** (a 10s clip = $1.40)
- Luma Ray2: Paid subscription (~$10-50/month depending on usage)
- Runway Gen-4.5: Via Replicate (pay-per-use, ~$0.05-0.10/second)
- Kling 3: Credits on signup (similar to Happy Horse)

**For zero-budget strategy**:
- Use Happy Horse via fal.ai free credits on signup (enough for initial testing)
- Use Fish Speech TTS (open-source, no cost)
- Use Groq Orpheus TTS (included with Groq API access)
- Fallback to ElevenLabs free tier (10K chars/month)

---

## Additional Finding: "qrog" TTS

**"qrog" refers to Groq Orpheus TTS**, the fastest TTS API available:
- **Speed**: Fastest TTS API (real-time generation)
- **Vocal directions**: Supports tags like `[cheerful]`, `[whisper]`, `[sad]` in prompts
- **Languages**: English (`canopylabs/orpheus-v1-english`) + Arabic Saudi (`canopylabs/orpheus-arabic-saudi`)
- **Cost**: Included with Groq API access (no separate billing)
- **API endpoint**: `https://api.groq.com/openai/v1/audio/speech`

This is the recommended TTS for the segment-based workflow because:
1. Fastest generation (critical for per-segment TTS)
2. Vocal direction controls allow emotional variation per segment
3. No additional cost beyond Groq API access

---

*Research completed: 2026-05-02*
*Sources: fal.ai documentation, API terms of service, 2026-era video generation benchmarks*
