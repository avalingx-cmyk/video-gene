# Budget-Friendly ($0) Text Overlay Solutions for AI-Generated Video

## The Problem
AI video generators (Runway, Luma, Kling, etc.) cannot render readable text from prompts. Text emerges garbled, misspelled, or illegible. The fix is to generate the video **without text**, then overlay text programmatically with perfect typography.

---

## Executive Summary: Recommended $0 Stack

| Use Case | Tool | Why |
|---|---|---|
| **Real-time Preview** | **HTML5 Canvas 2D** over `<video>` | Instant WYSIWYG, drag/resize/retime in the browser |
| **1080p Export** | **FFmpeg** server-side | Highest quality, no cost, full codec control |
| **User Editing** | **Single JSON model** → drives both Canvas preview & FFmpeg export | One source of truth for text tracks, positions, timings |

**The winning pattern:** Build a JSON text-track model (position, font, color, in/out times). Render it in real-time on an HTML5 Canvas layered over a `<video>` tag for editing/preview. When the user is satisfied, send the same JSON to a server running **FFmpeg** to burn the text into the final MP4.

---

## Detailed Comparison

### 1. FFmpeg — Server-Side Gold Standard ($0)

| Criteria | Rating | Details |
|---|---|---|
| Cost | $0 | Open source, runs on any VPS, laptop, or serverless container |
| Text Quality | Excellent | Native resolution, sub-pixel anti-aliasing, any TTF/OTF font |
| Font Support | Full | `fontfile=/path/to/font.ttf` — Google Fonts, custom brands |
| Position Control | Full | `x=(w-text_w)/2`, `y=50`, `x=main_w-overlay_w-40`, etc. |
| Timing Control | Full | `enable='between(t,5,10)'` or chain multiple drawtext filters |
| Animation | Partial | Fade via `fade` + overlay, scroll via `x=t*100`, no easing libraries |
| Performance | Batch | Not real-time; 1–3× video duration depending on CPU |
| Export Quality | Best-in-class | 1080p/4K, H.264/H.265, CRF control, 10-bit, HDR passthrough |

#### Code Example: Multi-Segment Text Overlay + TTS/BGM Mix

```bash
ffmpeg -i video_no_text.mp4 \
  -i tts_audio.mp3 \
  -i background_music.mp3 \
  -filter_complex "
    # 1) Overlay 'Introduction' at top-center, seconds 0–5
    [0:v]drawtext=fontfile=/usr/share/fonts/truetype/inter/Inter-Bold.ttf:
      text='Introduction':fontsize=72:fontcolor=white:
      x=(w-text_w)/2:y=80:
      borderw=4:bordercolor=black@0.6:
      enable='between(t\\,0\\,5)'[v1];

    # 2) Overlay 'Chapter 1' bottom-left, seconds 5–12
    [v1]drawtext=fontfile=/usr/share/fonts/truetype/inter/Inter-SemiBold.ttf:
      text='Chapter 1':fontsize=56:fontcolor=#FFD700:
      x=60:y=h-text_h-60:
      borderw=3:bordercolor=black@0.5:
      enable='between(t\\,5\\,12)'[v2];

    # 3) Audio: sidechain ducking — TTS ducks background music by 12dB
    [1:a][2:a]sidechaincompress=threshold=-20dB:ratio=4:attack=50:release=200:
      detection=peak:level_sc=0.3[aout]
  " \
  -map [v2] -map [aout] \
  -c:v libx264 -crf 18 -preset fast -movflags +faststart \
  -c:a aac -b:a 192k \
  output_1080p.mp4
```

**Key techniques for per-segment text:**
- `enable='between(t,start,end)'` toggles a single `drawtext` instance on/off.
- For overlapping text elements, chain `[0:v]drawtext... [v1]; [v1]drawtext... [v2]`.
- For many segments, generate an **ASS subtitle file** programmatically and use `-vf "ass=subtitles.ass"` — far more maintainable than a massive CLI.

**Limitations:**
- No real-time preview (unless you stream via HLS and reload, which is clunky).
- Complex multi-line layouts require ASS subtitles or multiple filters.
- Animation (slide, bounce) requires expression math, not designer-friendly.

**Best Use Case:** Final render pipeline, batch processing, guaranteed broadcast quality.

---

### 2. HTML5 Canvas + Video — Real-Time Preview King ($0)

| Criteria | Rating | Details |
|---|---|---|
| Cost | $0 | Browser-native, zero dependencies |
| Text Quality | Excellent | Vector text via `fillText()`, sub-pixel rendering, `shadowBlur` for outlines |
| Font Support | Full | `@font-face`, Google Fonts, variable fonts, icon fonts |
| Position Control | Full | Pixel coordinates, `%` via JS math, snap-to-grid, drag handles |
| Timing Control | Full | `video.currentTime` drives visibility via JSON track model |
| Animation | Full | CSS transitions, `requestAnimationFrame`, GSAP, Lottie — anything JS can do |
| Performance | Very Good | 1080×1920 @ 30fps is fine on modern GPUs; use offscreen canvas for static layers |
| Export Quality | Preview only | Browser cannot natively encode canvas+video to MP4 at 1080p without helper tools |

#### Code Example: Canvas Overlay Synced to Video

```html
<div id="stage" style="position:relative;width:360px;height:640px;">
  <video id="v" src="ai_video.mp4" style="width:100%;height:100%;"></video>
  <canvas id="c" width="1080" height="1920"
    style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;"></canvas>
</div>

<script>
const video = document.getElementById('v');
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d', { alpha: true });

// Text tracks (same JSON you will send to FFmpeg later)
const tracks = [
  { text: 'Introduction', start: 0, end: 5,
    x: 540, y: 200, font: '700 72px Inter', color: '#fff',
    outline: '#000', outlineWidth: 8, align: 'center' },
  { text: 'Swipe up →', start: 6, end: 10,
    x: 540, y: 1700, font: '600 56px Inter', color: '#FFD700',
    outline: '#000', outlineWidth: 6, align: 'center' }
];

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const t = video.currentTime;

  for (const tr of tracks) {
    if (t >= tr.start && t <= tr.end) {
      // Optional fade-in/out
      const fade = 0.3;
      let alpha = 1;
      if (t < tr.start + fade) alpha = (t - tr.start) / fade;
      if (t > tr.end - fade) alpha = (tr.end - t) / fade;
      ctx.globalAlpha = Math.max(0, Math.min(1, alpha));

      ctx.font = tr.font;
      ctx.textAlign = tr.align;
      ctx.lineWidth = tr.outlineWidth;
      ctx.strokeStyle = tr.outline;
      ctx.fillStyle = tr.color;

      const drawX = tr.align === 'center' ? tr.x : tr.x;
      ctx.strokeText(tr.text, drawX, tr.y);
      ctx.fillText(tr.text, drawX, tr.y);
      ctx.globalAlpha = 1;
    }
  }
  requestAnimationFrame(draw);
}
video.addEventListener('play', () => requestAnimationFrame(draw));
</script>
```

**Export from the Browser:**
- For *quick* exports, use `ffmpeg.wasm` (WebAssembly) in the browser to run the same FFmpeg commands client-side. Feasible for short clips, but heavy (~25MB WASM).
- For *production* exports, send the JSON track model to your backend and run native FFmpeg. Match the Canvas math exactly so WYSIWYG is guaranteed.

**Performance tips for 1080×1920:**
- Use `window.devicePixelRatio` scaling: set canvas.width = 1080 * dpr, then `ctx.scale(dpr, dpr)`.
- Separate static background from dynamic text layer using two stacked canvases.
- Avoid `shadowBlur` during scrubbing; enable it only for final-quality preview.

**Limitations:**
- No native “save as MP4” without `MediaRecorder` (quality/bandwidth limited) or `ffmpeg.wasm`.
- Slight frame drift possible if video and canvas are on different compositor threads; keep them in the same container and use `requestAnimationFrame`.

**Best Use Case:** In-browser editor, drag-and-drop positioning, live playback review, social-media-template builders.

---

### 3. Cloudinary — URL-Based Overlay (Free Tier: 25 Credits/Month)

| Criteria | Rating | Details |
|---|---|---|
| Cost | Limited Free | $0 for 25 transformation credits/month; then $89+/mo |
| Text Quality | Good | Rasterized text; crisp at intended size, softer if upscaled |
| Font Support | Good | Built-in fonts + upload your own + Google Fonts via `l_text` |
| Position Control | Good | `g_north`, `g_south_west`, `x_40,y_80` |
| Timing Control | Limited | Use `fl_layer_apply,so_5,eo_10` for start/end offsets per layer |
| Animation | None | Static text only; no fades or slides unless you chain video cuts |
| Performance | Excellent | CDN edge delivery; first request incurs transcoding latency |
| Export Quality | Good | Up to 1080p, H.264, adaptive bitrate |

#### Code Example: Cloudinary URL with Multiple Timed Text Layers

```
https://res.cloudinary.com/demo/video/upload/
  w_1080,
  l_text:Inter_70_bold:Introduction,co_white,b_rgb:00000080,g_north,y_80,
    fl_layer_apply,so_0,eo_5/
  l_text:Inter_56:Swipe_up,co_rgb:FFD700,g_south,y_120,
    fl_layer_apply,so_6,eo_10/
  ai_video.mp4
```

**Free Tier Reality Check:**
- 25 credits = roughly 25 video transformations per month.
- One 60-second video with two text layers = 1–2 credits.
- **Not viable for high-volume production**, but excellent for prototyping or low-volume SaaS.

**Limitations:**
- `so_` / `eo_` offset timing is relative to the video start, but complex multi-segment animations are painful to express in URLs.
- No real-time interactive preview; you must hit a URL and wait for the derived video.
- Custom font upload required for brand fonts; adds management overhead.

**Best Use Case:** Prototyping, low-volume automated thumbnails/clips, existing Cloudinary users.

---

### 4. Shotstack — JSON Video API (NOT Free)

| Criteria | Rating | Details |
|---|---|---|
| Cost | Paid only | 10 free trial credits; then $0.30/min PAYG or $39/mo subscription |
| Text Quality | Good | Vector-based render, 1080p output |
| Font Support | Good | Google Fonts, custom font upload |
| Position Control | Full | `x`, `y`, `width`, `height` in JSON |
| Timing Control | Full | `start`, `length` per clip/element |
| Animation | Good | Built-in fade, slide, zoom presets |
| Performance | Fast | Cloud render, ~seconds per short video |
| Export Quality | Good | 1080p, 60fps available |

**Why it’s not in the $0 stack:** After the 10-credit trial, minimum spend is ~$39/month or $75 one-time PAYG. Excellent API, but explicitly violates the “$0” constraint for ongoing use.

**Best Use Case:** Teams with budget who want a managed render API without operating FFmpeg servers.

---

### 5. Remotion — React-to-Video (Free for Individuals)

| Criteria | Rating | Details |
|---|---|---|
| Cost | Conditional $0 | Free for personal/individual creators; **$100/mo minimum for automators** |
| Text Quality | Excellent | React + CSS text = full web typography |
| Font Support | Full | Any web font, CSS `@font-face`, variable fonts |
| Position Control | Full | CSS absolute positioning, Flexbox, Grid |
| Timing Control | Full | Frame-accurate (30/60fps) via `<Sequence>` component |
| Animation | Excellent | CSS keyframes, GSAP, Framer Motion, spring physics |
| Performance | Preview real-time | Export via local FFmpeg or Lambda (costly) |
| Export Quality | Excellent | 1080p/4K, H.264/H.265/ProRes |

#### Code Example: Remotion Text Sequence

```tsx
import { Sequence, Video, AbsoluteFill } from 'remotion';

export const MyVideo = () => (
  <AbsoluteFill>
    <Video src={staticFile('ai_video.mp4')} />
    <Sequence from={0} durationInFrames={150}>
      <h1 style={{ position: 'absolute', top: 80, width: '100%', textAlign: 'center',
        fontFamily: 'Inter', fontSize: 72, color: 'white',
        textShadow: '0 4px 12px rgba(0,0,0,0.6)' }}>
        Introduction
      </h1>
    </Sequence>
    <Sequence from={180} durationInFrames={120}>
      <h1 style={{ position: 'absolute', bottom: 120, width: '100%', textAlign: 'center',
        fontFamily: 'Inter', fontSize: 56, color: '#FFD700',
        textShadow: '0 2px 8px rgba(0,0,0,0.6)' }}>
        Swipe up →
      </h1>
    </Sequence>
  </AbsoluteFill>
);
```

**Licensing Trap:**
- Remotion is free if you are an individual creator making content for yourself.
- If you build a SaaS, generate videos for end-users, or automate rendering: you need a **Company License** ($100/mo minimum per seat for v4; per-render pricing incoming in v5.0).
- `@remotion/player` is free to embed for preview.

**Best Use Case:** React shops building a video editor UI who eventually plan to pay for licensed rendering.

---

### 6. WebGL/Three.js Overlay — Overkill for Simple Text ($0)

| Criteria | Rating | Details |
|---|---|---|
| Cost | $0 | Open source |
| Text Quality | Good | SDF text (three-bmfont-text) or CanvasTexture — sharp but complex |
| Font Support | Moderate | Needs SDF atlas generation or runtime Canvas rendering |
| Position Control | Full | 3D coordinates, orthographic camera for 2D alignment |
| Timing Control | Manual | Per-frame update in `requestAnimationFrame` loop |
| Animation | Overkill | Full GPU particle systems, shaders — unnecessary for subtitles |
| Performance | High GPU use | Good for dozens of elements, but heavier than Canvas 2D for <10 text boxes |
| Export Quality | N/A | Requires same capture pipeline as Canvas (no native video encoder) |

**Why skip it:** For 2D text on video, Three.js adds shader compilation, scene graph, and texture atlas complexity with no visible benefit over Canvas 2D. It only makes sense if you are already doing 3D compositing.

---

## Comparison Matrix

| Approach | Cost | Preview | Export 1080p | Fonts | Timing | Animation | Edit UX |
|---|---|---|---|---|---|---|---|
| **FFmpeg** | $0 | ❌ | ✅ Best | TTF/OTF | `between(t)` | Math only | Config/JSON |
| **Canvas + Video** | $0 | ✅ Real-time | Via ffmpeg.wasm or backend | Web fonts | JS logic | ✅ Any JS | ✅ Drag/resize |
| **Cloudinary** | 25 cr/mo free | URL fetch | ✅ | Built-in + upload | `so/eo` | ❌ | URL params |
| **Shotstack** | $39/mo+ | Webhook poll | ✅ | Google/custom | JSON `start/length` | ✅ Presets | JSON API |
| **Remotion** | Free / $100+ | `@remotion/player` | ✅ | Web fonts | `<Sequence>` | ✅ React/CSS | React code |
| **Three.js** | $0 | ✅ | Via capture | SDF/Canvas | Manual loop | Shader/GPU | Code |

---

## Recommended Architecture: The “One JSON, Two Engines” Stack

To get a $0, high-quality, editable text-overlay pipeline, combine **HTML5 Canvas** (preview/editor) and **FFmpeg** (export). Both consume the same JSON schema so there is no mismatch between what the user sees and what gets rendered.

### Shared Text Track Schema

```json
{
  "version": 1,
  "canvas": { "width": 1080, "height": 1920 },
  "tracks": [
    {
      "id": "intro",
      "type": "text",
      "text": "Introduction",
      "start": 0.0,
      "end": 5.0,
      "style": {
        "fontFamily": "Inter",
        "fontWeight": 700,
        "fontSize": 72,
        "color": "#ffffff",
        "outlineColor": "#000000",
        "outlineWidth": 4,
        "align": "center"
      },
      "position": { "x": 540, "y": 200, "anchor": "center" }
    },
    {
      "id": "cta",
      "type": "text",
      "text": "Swipe up →",
      "start": 6.0,
      "end": 10.0,
      "style": {
        "fontFamily": "Inter",
        "fontWeight": 600,
        "fontSize": 56,
        "color": "#FFD700",
        "outlineColor": "#000000",
        "outlineWidth": 3,
        "align": "center"
      },
      "position": { "x": 540, "y": 1720, "anchor": "center" }
    }
  ]
}
```

### Frontend: Canvas Preview + Drag Editor

- Render the `<video>` at 360×640 (or native) for preview.
- Layer a transparent `<canvas>` on top. Draw text tracks from the JSON using `fillText()`.
- Sync every `requestAnimationFrame` to `video.currentTime`.
- Add pointer-event listeners on the canvas for drag-to-move and double-tap-to-edit.
- When the user scrubs, text updates instantly.

### Backend: FFmpeg Export

- Accept the same JSON via API.
- Generate a filtergraph string or an ASS subtitle file from the JSON.
- Run FFmpeg with `-c:v libx264 -crf 18` for visually lossless 1080p.
- Mix in TTS and BGM with `sidechaincompress` for professional ducking.
- Return the MP4.

### Why this wins on every criteria

| Criteria | How the stack delivers |
|---|---|
| Cost | $0. Canvas = browser. FFmpeg = open source on your server. |
| Text Quality | Canvas 2D and FFmpeg `drawtext` both render vector fonts at native res. |
| Font Support | Load any font via `@font-face` in the browser; reference the same TTF on the server. |
| Position Control | Drag on canvas → store `x,y` in JSON → FFmpeg uses identical coordinates. |
| Timing Control | Scrub handles in UI update `start/end` in JSON; FFmpeg burns the same windows. |
| Animation | Canvas animates with JS; FFmpeg approximates with `fade`/`scroll` or you export ASS with \`t` tags for advanced tweening. |
| Preview Performance | 60fps scrubbing on modern laptops/phones at 1080p canvas. |
| Export Quality | Unmatched: x264, AAC, CRF 18, faststart for streaming. |

---

## Quick-Start Code: Node.js FFmpeg Generator

```js
const { execSync } = require('child_process');

function buildFilter(tracks, w, h) {
  let filter = '[0:v]';
  let label = 'v0';

  tracks.forEach((tr, i) => {
    const next = `v${i + 1}`;
    const font = tr.style.fontFamily.replace(/\s/g, '');
    const size = tr.style.fontSize;
    const color = tr.style.color;
    const outline = tr.style.outlineWidth || 0;
    const outCol = tr.style.outlineColor || 'black';
    const x = tr.position.x;
    const y = tr.position.y;
    const align = tr.style.align === 'center' ? 'center' : 'left';
    const start = tr.start;
    const end = tr.end;

    // Escape for FFmpeg
    const text = tr.text.replace(/'/g, "'\\''");

    filter += `drawtext=fontfile=/usr/share/fonts/truetype/${font}.ttf:` +
      `text='${text}':fontsize=${size}:fontcolor=${color}:` +
      `x=${x}-text_w/2:y=${y}:` + // adjust anchor logic as needed
      `borderw=${outline}:bordercolor=${outCol}@0.6:` +
      `enable='between(t\\,${start}\\,${end})'`;

    filter += i < tracks.length - 1 ? `[${next}];[${next}]` : '';
  });

  return filter;
}

const json = require('./tracks.json');
const vf = buildFilter(json.tracks, 1080, 1920);
const cmd = `ffmpeg -y -i video.mp4 -filter_complex "${vf}" -c:v libx264 -crf 18 -c:a copy output.mp4`;
execSync(cmd, { stdio: 'inherit' });
```

---

## Audio Mixing Deep Dive: TTS + Background Music

AI-generated videos usually need narration (TTS) plus background music. The professional trick is **sidechain compression**: the music automatically dips when the TTS speaks.

```bash
ffmpeg -i video.mp4 -i tts.mp3 -i music.mp3 -filter_complex "
  [1:a][2:a]sidechaincompress=threshold=-24dB:ratio=6:attack=20:release=250:
    detection=peak:level_sc=0.25[aout]
" -map 0:v -map [aout] -c:v copy -c:a aac -b:a 192k output.mp4
```

- `threshold=-24dB` — when TTS exceeds this, music ducks.
- `ratio=6` — aggressive dip for clarity.
- `attack=20ms` — fast reaction so the first word is always audible.
- `release=250ms` — smooth recovery so music doesn’t pump distractingly.

If you want simple mixing without ducking, use `amix`:

```bash
ffmpeg -i video.mp4 -i tts.mp3 -i music.mp3 -filter_complex "
  [1:a]volume=1.0[tts];
  [2:a]volume=0.25[music];
  [tts][music]amix=inputs=2:duration=longest[aout]
" -map 0:v -map [aout] -c:v copy -c:a aac -b:a 192k output.mp4
```

---

## Final Recommendation

1. **Start with Canvas + FFmpeg today.** It is the only combination that gives you real-time drag-and-drop editing, brand-perfect fonts, and broadcast-quality export for exactly $0.
2. **Use a shared JSON model.** Never hard-code coordinates in FFmpeg CLI by hand — generate it from the same data structure that drives your Canvas renderer.
3. **If you outgrow self-hosted FFmpeg**, evaluate Remotion (if you are React-native) or Shotstack (if you want a managed API). Both cost money, but the migration is straightforward because your track-model JSON maps cleanly to their JSON schemas.
4. **Avoid Cloudinary for heavy video pipelines** — the free tier is too small, and per-transformation pricing becomes expensive compared to running your own FFmpeg workers.
5. **Skip WebGL/Three.js** unless your video project is already inside a 3D scene. Canvas 2D is simpler, faster to develop, and renders equally crisp text.
