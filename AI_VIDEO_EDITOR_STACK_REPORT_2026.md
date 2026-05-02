# AI-Powered Video Editor: Technology Stack Report (2026)

> **Date:** 2026-05-02  
> **Scope:** Tools and APIs for a Canva-like, browser-based AI video editor with programmatic generation, text overlay, audio mixing, and MP4 export.

---

## 1. Executive Summary

To build a browser-based AI video editor in 2026, you need a **hybrid architecture**: a real-time preview layer in the browser and a server-side rendering pipeline for final export. The only tool that natively unifies both preview and render via the same code is **Remotion**. For teams that prefer a simpler JSON-to-video API, **Shotstack** is the best managed alternative. **FFmpeg** remains the universal backend for final assembly, audio mixing, and text burn-in. **Cloudinary** is excellent for on-the-fly image/text overlays and asset optimization but is not a full video editor. **Canva has no headless programmatic video API**—it only offers an in-editor Apps SDK.

**Top Recommendation:** A **Remotion + React + FFmpeg** stack. Use Remotion Player for the preview/editor UI, React for the drag-and-drop surface, and Remotion Renderer (or FFmpeg) for the final MP4 export.

---

## 2. Architecture Map

| Step | Requirement | Best Tool(s) |
|------|-------------|--------------|
| 1 | AI generates video footage | Runway, Pika, Kling, or Stable Video Diffusion (external) |
| 2 | AI generates text content | GPT-4o / Claude via standard REST APIs |
| 3 | AI generates audio | Groq Orpheus TTS + MusicGen/Suno for BGM |
| 4 | Overlay text + mix audio | **FFmpeg** (final render) or **Remotion** (unified) |
| 5 | Browser review & edit | **Remotion Player** + **React DnD** / **Fabric.js** |
| 6 | Export final MP4 | **Remotion Renderer**, **Shotstack**, or **FFmpeg** |

---

## 3. Master Comparison Table

| Tool / Approach | Cost | Text Rendering Quality | Ease of Implementation | Real-Time Preview? | Best For |
|-----------------|------|------------------------|------------------------|--------------------|----------|
| **FFmpeg** (Server) | Free (infra only) | Excellent (libass, drawtext, subtitle burn-in) | Hard | No | Final assembly, audio ducking, reliable server-side export |
| **Remotion** | Free–$500+/mo | Excellent (React/DOM/CSS + any web font) | Medium | **Yes** (Player) | End-to-end React video apps; same code for preview & render |
| **Shotstack API** | ~$0.20–$0.30/min | Good (TextAsset, RichTextAsset) | Easy | No (async webhooks) | High-volume template-based rendering; no UI needed |
| **Cloudinary Transformations** | Free–$249+/mo | Good (`l_text` overlays, Google Fonts) | Very Easy | Near-real-time (CDN URL) | Dynamic asset delivery, simple overlays, optimization |
| **Browser Canvas 2D** | Free | Excellent (web fonts, vector paths) | Medium | **Yes** | Editor UI / preview layer only (requires separate renderer) |
| **Fabric.js** | Free | Excellent (interactive objects) | Medium | **Yes** | Drag-and-drop text/sticker editor surface |
| **Canva Apps SDK** | Free to build | N/A (inside Canva only) | Medium | Yes | Only if you want users to edit *inside* Canva itself |
| **Happy Horse Endpoint** | Unknown | Unknown | Unknown | Unknown | **Unverified / Not found** in public documentation |

---

## 4. Deep Dive by Category

### 4.1 Video Composition Tools

#### FFmpeg
The industry standard command-line multimedia framework.
- **Text Overlay:** `drawtext` filter (basic) or `subtitles` filter (advanced typography via ASS/SSA).
- **Audio Mixing:** `amix`, `amerge`, `sidechaincompress` for ducking.
- **Pros:** Free, handles any format, pixel-perfect control.
- **Cons:** No browser preview; steep learning curve; filtergraph syntax is verbose.
- **Key Command Example:**
```bash
ffmpeg -i footage.mp4 -i tts.mp3 -i bgm.mp3 \
  -filter_complex "
    [1:a]volume=1.0[tts];
    [2:a]volume=0.25[bgm];
    [tts][bgm]amix=inputs=2:duration=longest[aout];
    [0:v]drawtext=text='Hello World':x=(w-text_w)/2:y=50:fontsize=48:fontcolor=white[outv]
  " \
  -map "[outv]" -map "[aout]" -c:v libx264 -y output.mp4
```

#### Remotion
A React framework for programmatic video creation.
- **Composition:** Write React components that render to MP4 frames.
- **Render:** `@remotion/renderer` (Node.js) or **Remotion Lambda** (AWS serverless).
- **Pricing:**
  - Free for individuals & teams ≤3.
  - Remotion for Automators: **$100/mo minimum** (~$0.01/render).
  - Enterprise: **$500+/mo**.
- **Pros:** Identical code for preview and export; any CSS/web font works; Remotion Player gives timeline + scrubbing out of the box.
- **Cons:** Requires React expertise; self-hosting or Lambda costs for rendering.

#### Shotstack API
A cloud video editing API powered by JSON timelines.
- **Endpoint:** `POST https://api.shotstack.io/edit/v1/render`
- **Composition:** Define tracks, clips, assets (video, image, text, audio) in JSON.
- **Text:** `TextAsset`, `TitleAsset`, or `RichTextAsset` with custom fonts.
- **Pricing:**
  - PAYG: **$0.30/minute** (min $75).
  - Subscription: **$0.20/minute** (from $39/mo).
- **Pros:** No video infrastructure to manage; fast renders; white-label editor SDK available.
- **Cons:** Async only (webhook polling for status); preview must be built separately.

#### Cloudinary Video Transformations
URL-based (or SDK-based) on-the-fly transformations.
- **Text Overlay:** `l_text:font_size:MyText/fl_layer_apply`.
- **Audio Overlay:** `l_audio:myfile/fl_layer_apply` with `e_volume`.
- **Pricing:**
  - Free: 25 monthly credits.
  - Plus: **$99/mo** (225 credits).
  - Advanced: **$249/mo** (600 credits).
- **Pros:** CDN delivery; instant URL changes; excellent for dynamic text on existing videos.
- **Cons:** Not a generalized video editor—complex timeline editing is cumbersome or impossible; text styling is limited compared to DOM/CSS.

### 4.2 Text Overlay on Video

| Approach | Quality | Implementation | Notes |
|----------|---------|----------------|-------|
| **Server-side FFmpeg drawtext** | Good (basic), Excellent (via ASS subtitles) | Hard | Best for final burn-in. |
| **Server-side Remotion/React** | Excellent | Medium | Uses full CSS—any font, gradient, shadow, animation. |
| **Cloudinary `l_text`** | Good | Very Easy | Limited to Cloudinary's supported font list and styling options. |
| **Browser Canvas 2D `fillText`** | Excellent | Medium | Perfect for editor preview; must be re-rendered server-side for export. |
| **Browser DOM overlay (HTML/CSS)** | Excellent | Easy | Best fidelity in preview; sync with `<video>` time. |

**Recommendation:** Use **DOM overlay** (or Fabric.js) for the editor preview and **Remotion** (or FFmpeg) for the final burn-in.

### 4.3 Audio Mixing

| Tool | Ducking TTS over BGM | How |
|------|----------------------|-----|
| **FFmpeg** | Yes | `sidechaincompress` or volume envelope scripting. |
| **Remotion** | Indirect | Use separate audio tracks; precise volume keyframes via props. |
| **Shotstack** | Basic | `volume` per clip; `Soundtrack` volume control. |
| **Cloudinary** | Basic | `e_volume` on audio overlays. |

**FFmpeg Audio Ducking Example:**
```bash
ffmpeg -i tts.mp3 -i bgm.mp3 -filter_complex \
  "[1:a]asplit=2[bgm][bgm2];
   [bgm][0:a]sidechaincompress=threshold=-20dB:ratio=4:attack=50:release=200[ducked];
   [ducked][bgm2]amix=inputs=2:duration=longest[final]" \
  -map "[final]" output.mp3
```

### 4.4 Browser-Based Editors

| Library | Use Case | Drag & Drop? | Learning Curve |
|---------|----------|--------------|----------------|
| **Canvas 2D API** | Lightweight preview, drawing text/shapes | Manual | Medium |
| **Fabric.js** | Full interactive canvas (text, images, rotation) | Yes | Medium |
| **React + React-DnD** | DOM-based draggable text overlays | Yes | Low |
| **Remotion Player** | Timeline + video preview + parameter controls | Built-in scrubbing | Medium |

**Recommended Editor UI Pattern:**
- **Base layer:** `<video>` element playing generated footage.
- **Overlay layer:** Absolutely positioned `<div>` elements (or Fabric.js canvas) for text, synced to `video.currentTime`.
- **Controls:** A scrubber/timeline using Remotion Player or a custom React component.
- **State:** JSON object tracking each text element's `{x, y, text, fontFamily, fontSize, startTime, endTime}`.

### 4.5 Real-Time Preview

The only mature solution that gives you **WYSIWYG real-time preview** before server rendering is **Remotion Player**.

```tsx
import { Player } from "@remotion/player";
import { MyVideo } from "./MyVideo";

<Player
  component={MyVideo}
  durationInFrames={300}   // 5s @ 60fps
  fps={60}
  compositionWidth={1920}
  compositionHeight={1080}
  inputProps={{ title: "Hello World" }}
/>
```

For non-Remotion stacks, you must sync HTML5 `<video>` with a canvas/DOM overlay and manually calculate positions per frame during `requestAnimationFrame`. This is doable but requires significant custom engineering.

### 4.6 Happy Horse Video-Edit Endpoint

**Status: Unverified / Not Found**
No public documentation, API reference, or developer portal for a "Happy Horse video-edit endpoint" was discovered during this research (May 2026). It may refer to:
- An internal/private service within a specific organization.
- A rebranded or defunct tool.
- A hallucinated or placeholder name.

**Recommendation:** Do not plan your stack around this endpoint unless you can provide official documentation or a base URL.

### 4.7 Canva API

**Critical Finding:** There is **no headless Canva API for programmatic video composition** as of 2026.
- Canva offers the **Apps SDK**, which lets you build plugins that run **inside** the Canva editor iframe.
- You can add elements to a user's design and automate tasks, but this requires an active user editing session inside Canva.com.
- You **cannot** send a JSON payload from your backend to Canva and receive an MP4.

**Verdict:** If your goal is a standalone white-label editor (like Canva but on your own domain), this is not viable. Use Remotion or Shotstack instead.

---

## 5. Final Recommendation: The Best Stack

For the architecture you described, the optimal 2026 stack is:

### Tier 1: The "Remotion-Native" Stack (Best WYSIWYG)

| Layer | Technology |
|-------|------------|
| **Frontend Editor** | React + **Remotion Player** (`@remotion/player`) + **React-DnD** or **Fabric.js** |
| **Preview Sync** | Remotion timeline/scrubber + DOM/CSS text overlays |
| **Backend Render** | **Remotion Renderer** (`@remotion/renderer`) on Node.js server, or **Remotion Lambda** |
| **Audio Pipeline** | FFmpeg (ducking/mixing) invoked after Remotion render, or Web Audio tracks mixed in-browser before upload |
| **AI Integrations** | GPT-4o (scripts), Groq Orpheus (TTS), Replicate/Runway (footage) |

**Why this wins:** The text styles, fonts, and animations you see in the browser during editing are **identical** to the final MP4 because Remotion renders the same React components headlessly. This eliminates the classic "preview vs. final mismatch" problem.

### Tier 2: The "JSON + Managed Render" Stack (Fastest to Market)

| Layer | Technology |
|-------|------------|
| **Frontend Editor** | React + HTML5 Video + Canvas 2D overlay (for preview) |
| **State** | JSON timeline object |
| **Backend Render** | **Shotstack API** (`POST /render`) |
| **Hosting** | Shotstack handles all encoding/scaling |

**Why this wins:** You don't build a render farm. You build the UI, post JSON, and get an MP4 via webhook. The trade-off is that preview fidelity might differ slightly from Shotstack's final output, and per-minute costs are higher at scale.

### Tier 3: The "Bare Metal" Stack (Lowest Cost, Highest Effort)

| Layer | Technology |
|-------|------------|
| **Frontend Editor** | React + Fabric.js + HTML5 Video |
| **Backend Render** | **FFmpeg** on a VPS / ECS / Lambda container |
| **Storage/CDN** | S3 + CloudFront |

**Why this wins:** Lowest marginal cost per video. You own every pixel. The trade-off is months of engineering to build preview syncing, frame-accurate scrubbing, and a stable rendering queue.

---

## 6. Quick Reference: APIs & Pricing

| Service | Key Endpoint / Package | Pricing (2026) |
|---------|------------------------|----------------|
| **Shotstack Render** | `POST https://api.shotstack.io/edit/v1/render` | $0.20–$0.30/min |
| **Cloudinary Transform** | `https://res.cloudinary.com/{name}/video/upload/{transform}/{id}.mp4` | Free–$249/mo |
| **Remotion Player** | `npm i @remotion/player` | Free (≤3 people) |
| **Remotion Renderer** | `npm i @remotion/renderer` | Free / Commercial $100+ |
| **FFmpeg** | `ffmpeg` command | Free (open source) |
| **Canva Apps SDK** | `npm i @canva/appsdk` | Free to build; no headless render |

---

## 7. Sample Integration Pattern (Remotion)

```tsx
// MyVideo.tsx — used in both Player and Renderer
import { AbsoluteFill, useVideoConfig, useCurrentFrame } from "remotion";

export const MyVideo = ({ title, ttsSrc, bgmSrc }) => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <video src="https://cdn.example.com/ai-footage.mp4" />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <h1
          style={{
            fontFamily: "Inter",
            fontSize: "80px",
            color: "white",
            textShadow: "0px 4px 20px rgba(0,0,0,0.5)",
          }}
        >
          {title}
        </h1>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// server.ts — headless render
import { renderMedia } from "@remotion/renderer";

await renderMedia({
  composition: {
    id: "my-video",
    component: MyVideo,
    durationInFrames: 300,
    fps: 60,
    width: 1920,
    height: 1080,
  },
  serveUrl: bundledUrl,
  codec: "h264",
  outputLocation: "out.mp4",
});
```

---

## 8. Conclusion

- **If you need a Canva-like browser editor with exact WYSIWYG export:** Use **Remotion** + **React** for preview and render, with **FFmpeg** for advanced audio ducking.
- **If you want to ship fast and don't mind paying per minute:** Use **Shotstack** for rendering and build a Canvas 2D preview.
- **If you only need dynamic text overlays on existing videos:** Use **Cloudinary** transformations.
- **Avoid** relying on a "Canva API" or "Happy Horse" endpoint for headless video composition—they either don't exist for that purpose or are unverified.
