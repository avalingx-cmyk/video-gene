# Research Report: Segment-Based Video Generation vs. Full-Video Generation

## Executive Summary

The **segment-based workflow** (5-15s clips stitched together with transitions, TTS audio, and review) is **significantly better** than the original full-video generation approach for the following reasons:

1. **Quality**: Short segments (5-15s) generate at higher fidelity than long videos (30s-5min)
2. **Editability**: Segments can be reviewed, reordered, and adjusted before final export
3. **Reliability**: If one segment fails, others can still be used (fault tolerance)
4. **Audio sync**: Per-segment TTS + native audio + BGM = professional audio mix
5. **Longer videos**: Can produce 30s to 5+ minutes by stitching 3-10 segments

---

## 1. Problem with Full-Video Generation (Original Plan)

### How it works:
- Single API call generates the entire video (30s to 5min)
- One-shot output with no intermediate review

### Why it fails:
1. **Quality degradation with length**: AI video models produce worse results for longer videos. Motion coherence, character consistency, and scene transitions degrade significantly beyond 10-15 seconds.

2. **No review workflow**: If the output is bad, the entire generation is wasted. No way to fix a single bad segment without regenerating everything.

3. **Audio sync issues**: Adding voiceover/BGM to a pre-generated video requires precise timing alignment. If the video doesn't match the narration, the entire video is unusable.

4. **API limitations**:
   - ZSky AI: 10s max per clip (from original plan)
   - Happy Horse: 15s max per clip
   - Luma Ray2: 10s max per clip
   - Runway Gen-4.5: 10s max per clip
   - **None of these APIs support 30s-5min in a single call**

5. **No editing**: Cannot change titles, transitions, or audio after generation without regenerating.

---

## 2. Segment-Based Workflow (New Idea)

### How it works:
1. User provides a text prompt (or .md/.pdf)
2. Prompt enhancer splits the prompt into 3-5 segment scripts (5-15s each)
3. Each segment is generated independently by video API (Happy Horse, Luma, Runway)
4. TTS audio is generated per segment (Groq Orpheus "qrog", ElevenLabs, Fish Speech)
5. Background music is selected based on content type
6. All segments + audio are displayed in a timeline editor (Remotion Player)
7. User can:
   - Preview low-res 360p version
   - Edit titles per segment
   - Change transitions (fade, wipe, slide)
   - Reorder segments
8. User approves → FFmpeg composes final 1080p MP4
9. Optional: Upload to YouTube, trigger n8n workflow

### Why it succeeds:

#### A. Quality
- **Each segment is 5-15s**: Within the optimal range for all video APIs
- **Happy Horse via fal.ai**: #1 ranked, 1080p+audio, 9:16 native
- **Luma Ray2**: Top Elo, keyframe support, extendable
- **Runway Gen-4.5**: Highest quality, native audio
- **Character consistency**: Reference images + last-frame conditioning

#### B. Editability
- **Timeline editor**: Remotion Player in browser (1080x1920 preview)
- **Title overlays**: Per-segment text with styling
- **Transitions**: Fade, wipe, slide between segments
- **Audio mixing**: TTS + BGM + native video audio via FFmpeg
- **Low-res preview**: 360p for fast review before final export

#### C. Reliability
- **Fault tolerance**: If segment 3 fails, segments 1-2 and 4-5 can still be used
- **Provider fallback**: Happy Horse → Luma → Runway → Kling (auto-switch on failure)
- **Retry logic**: Exponential backoff for transient API failures

#### D. Longer Videos
- **3 segments × 15s = 45s** (YouTube Shorts)
- **5 segments × 15s = 75s** (TikTok/Reels)
- **10 segments × 15s = 150s** (2.5min — within API limits)
- Can extend further by using Luma Ray2's extendable clips

#### E. Audio
- **Groq Orpheus ("qrog")**: Fastest TTS, vocal directions ([cheerful], [whisper])
- **ElevenLabs**: 32+ voices, 10K chars free/mo
- **Fish Speech**: Open-source, 80+ languages, Apache 2.0
- **Per-segment TTS**: Each segment gets its own narration, perfectly timed
- **FFmpeg mixing**: AAC codec, crossfades, audio-video sync

---

## 3. Technical Comparison

| Criteria | Full-Video (Old) | Segment-Based (New) | Winner |
|----------|-------------------|---------------------|--------|
| **Video length** | 30s-5min (but APIs limit to 10-15s) | 30s-5min (by stitching segments) | **New** |
| **Quality** | Degrades after 10s | Optimal at 5-15s per segment | **New** |
| **Editability** | None (one-shot) | Full timeline editor | **New** |
| **Review workflow** | None | Low-res preview → edit → export | **New** |
| **Audio sync** | Manual, error-prone | Per-segment TTS + FFmpeg mix | **New** |
| **Fault tolerance** | All-or-nothing | Partial (per-segment) | **New** |
| **API cost** | 1 API call per video | 3-5 API calls per video | **Old** (cheaper) |
| **Implementation complexity** | Low | Medium-High | **Old** (simpler) |
| **User experience** | Prompt → wait → video | Prompt → segments → edit → video | **New** (better UX) |
| **n8n integration** | Single webhook | Per-segment status + final webhook | **New** (more granular) |

**Trade-off**: The segment-based approach costs more API calls (3-5x) but delivers significantly better quality, editability, and reliability. For a creator economy product, the UX improvement justifies the cost.

---

## 4. API Compatibility Analysis

### Primary: Happy Horse via fal.ai
- **Max duration**: 15s per segment ✅
- **Resolution**: 1080p, 9:16 native ✅
- **Audio**: Native audio synchronized ✅
- **Free tier**: Credits on signup ✅
- **Best for**: Primary segment generation

### Secondary: Luma Ray2
- **Max duration**: 10s per segment ✅
- **Resolution**: 1080p, 9:16 native ✅
- **Audio**: Native audio ✅
- **Extendable**: Can extend clips ✅
- **Best for**: Quality-sensitive segments

### Tertiary: Runway Gen-4.5
- **Max duration**: 10s per segment ✅
- **Resolution**: 1080p, 9:16 native ✅
- **Audio**: Native audio ✅
- **Best for**: Segments requiring highest quality

### Fallback: Kling 3 via fal.ai
- **Max duration**: 15s per segment ✅
- **Multi-shot**: Character consistency ✅
- **Best for**: Character-driven segments

**Conclusion**: All major video APIs support 5-15s segments natively. None support 30s-5min in a single call. The segment-based approach is the **only viable way** to produce longer videos with these APIs.

---

## 5. Content Type Suitability

| Content Type | Segment-Based Works? | Why |
|--------------|----------------------|-----|
| **Educational** | ✅ Excellent | Step-by-step segments match lesson structure |
| **Marketing** | ✅ Excellent | Product shots + transitions = polished ads |
| **Technology** | ✅ Good | Code demos + explanations in segments |
| **Storytelling** | ✅ Good | Scene-by-scene narrative flow |
| **Music videos** | ⚠️ Moderate | Needs precise audio-video sync |
| **Live events** | ❌ Poor | Real-time footage not suitable for AI generation |

---

## 6. Cost Analysis (Zero Budget)

| Component | Full-Video (Old) | Segment-Based (New) |
|-----------|-------------------|---------------------|
| Video generation | 1 API call/video | 3-5 API calls/video |
| TTS voiceover | 1 call/video | 3-5 calls/video |
| Background music | 1 call/video | 1 call/video |
| **Total API calls** | 3/video | 10-11/video |
| **Happy Horse (fal.ai)** | Free credits on signup | Same (per-segment) |
| **Groq Orpheus (qrog)** | Included with API | Same (per-segment) |
| **Fish Speech** | Self-hosted (free) | Same (self-hosted) |

**Mitigation for higher cost**:
- Use open-source Fish Speech instead of ElevenLabs for budget-conscious users
- Cache generated segments for reuse
- Implement per-user rate limiting (10 req/min)
- Provider fallback skips paid tiers when free tier exhausted

---

## 7. Risk Assessment

| Risk | Full-Video (Old) | Segment-Based (New) |
|------|-------------------|---------------------|
| API goes down | Entire video fails | Other segments still work |
| One segment bad | Entire video bad | Regenerate only that segment |
| Audio misaligned | Entire video unusable | Fix per-segment audio |
| User wants changes | Regenerate everything | Edit timeline directly |
| Long video (5min) | API may timeout or fail | Stitched from 20 segments |
| Copyright claims | Entire video at risk | Per-segment attribution |

---

## 8. Recommendation

### ✅ Segment-based workflow is the correct approach.

**Reasons:**
1. **API reality**: No free video API supports 30s-5min in a single call. The segment-based approach is the only way to produce longer videos.
2. **Quality**: Short segments (5-15s) generate at much higher quality than long videos.
3. **User experience**: Review → Edit → Export workflow is dramatically better than one-shot generation.
4. **Reliability**: Fault tolerance, retry logic, and provider fallback make the system robust.
5. **Audio**: Per-segment TTS + FFmpeg mixing produces professional audio tracks.
6. **Future-proof**: Can add more segments for longer videos without API changes.

### ⚠️ Caveats:
1. **Higher API cost**: 3-5x more API calls per video. Mitigated by free tiers + open-source TTS.
2. **Implementation complexity**: Requires Remotion frontend + FFmpeg backend. But the existing codebase already has FastAPI + Celery scaffold.
3. **Storage**: Need cloud storage (S3/R2) for segments + final videos. R2 has generous free egress.

---

## 9. Next Steps (If Approved)

1. **Update plan.md**: Replace full-video architecture with segment-based workflow
2. **Update implementation.md**: Add segment models, Remotion frontend, FFmpeg composition
3. **Research agent**: Verify 2026 API pricing and free-tier limits
4. **Prototype**: Generate 3 segments with Happy Horse, stitch with FFmpeg, review in browser
5. **Test**: Educational, marketing, technology prompts across all content types

---

*Report by: Megatron, Supreme Commander of the Decepticons*
*Date: 2026-05-02*
