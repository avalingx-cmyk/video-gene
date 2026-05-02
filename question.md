# Questions & Answers for Video Creator Project

## Technical Specifications
1. **Video length**: 30 seconds minimum, up to 5+ minutes
2. **Resolution**: 1080x1920 (portrait/mobile)
3. **Audio support**: Yes — background music and voiceover
4. **Content styles**: Educational, marketing, and technology videos for YouTube
5. **Prompt complexity**: Both simple and complex scenes supported

## Input Formats
6. **Text prompts**: Yes (primary)
7. **File uploads**: .md and .pdf files supported
8. **Image references**: Yes — users can attach images to prompts for image-to-video
9. **Video-to-video**: No (text-to-video only for now)

## Output & Editing
10. **Output format**: MP4 only
11. **Post-generation editing**: Yes — trimming and concatenation
12. **Watermark**: No

## User Experience
13. **Target audience**: Parents, kids, social media users, YouTube creators (tech/marketing focus)
14. **User technical level**: Mixed — users learning new tech or solving problems
15. **Interface**: Simple mode for now (no advanced controls)

## Deployment & Infrastructure
16. **Platform**: Web app
17. **Usage pattern**: Both occasional and heavy usage; n8n automation support needed
18. **Latency requirements**: Flexible
19. **Budget**: $0 — fully cloud-based using third-party APIs (no self-hosted GPU)
20. **Connectivity**: Online only

## Integrations
21. **Content creation tools**: No direct integration
22. **Publishing**: Yes — YouTube with scheduled publishing
23. **Developer API**: Yes — planning for n8n first, then others
24. **Other automation**: Open to additional integrations

## Safety & Ethics
25. **Content filters**: No 18+ content, no harmful content
26. **Copyright**: Needs research
27. **Misuse prevention**: Needs research
28. **Data privacy**: User-only access, no external exposure

## Operations & Reliability
29. **Job queuing**: Yes — video generation APIs are async with long wait times; need job queue with status polling and webhook callbacks
30. **Retry strategy**: Automatic retry on API failure with exponential backoff, then fallback to next provider in router chain
31. **Error notifications**: In-app status updates; email notification on completion or failure for long jobs
32. **Rate limiting**: Per-user rate limits to stay within free-tier API quotas; queue excess requests

## User Management
33. **Authentication**: Simple email/password or OAuth (Google) — lightweight for now
34. **Multi-user**: Yes — each user has their own video library, prompts, and scheduled publishes
35. **User roles**: Single role for now (no admin/creator distinction yet)

## Audio Details
36. **Voiceover languages**: English only for now
37. **Voice style**: Natural/conversational for educational; professional for marketing/tech
38. **Background music style**: Matches video content type — user does not select manually (auto-determined by prompt enhancer)
39. **User audio upload**: No — audio is generated only, no custom audio uploads for now

## n8n Integration Details
40. **Trigger direction**: Both — n8n can trigger video generation via webhook, and completed videos can trigger n8n workflows
41. **Payload format**: JSON with prompt, settings, and callback URL for async completion
42. **Authentication for API**: API key per user for developer/n8n access

## Open Research Items
43. **Copyright**: Do generated videos from AI models have clear usage rights? Do any APIs claim ownership?
44. **Misuse prevention**: What detection methods work for deepfake-style content generation?
45. **API portrait support**: Which video generation APIs actually support 1080x1920 output natively vs. requiring post-crop?

## Open Questions for Architecture Decision (DIN-64)

The following questions need user clarification before final implementation begins:

46. **Brand logo handling** — Should the system auto-detect brand colors from a logo upload, or does the user input hex codes manually?
47. **Font library** — Use Google Fonts (free) or support custom brand font uploads?
48. **Template system** — Pre-built templates for educational/marketing/tech (like Canva), or start from scratch every time?
49. **Music licensing** — Use AI-generated music (Suno — no copyright issues) or a licensed royalty-free library (Epidemic Sound, Artlist)?
50. **Export formats** — MP4 only, or also GIF/WebM for social platforms?
51. **Editor budget commitment** — Commit to the $0 FFmpeg + Canvas 2D stack, or budget for Remotion ($100/mo) for professional preview/export?
52. **Free tier exhaustion strategy** — If Happy Horse free credits run out, should we cap per-user generation or prompt for payment/upgraded plan?

*Added: 2026-05-02 (Megatron, DIN-64 architecture decision)*
