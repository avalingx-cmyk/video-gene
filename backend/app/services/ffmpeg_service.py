import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import ffmpeg

from app.core.config import get_settings

logger = logging.getLogger(__name__)
SETTINGS = get_settings()

TRANSITION_TYPES = {
    "fade": "fade",
    "fadeblack": "fadeblack",
    "fadewhite": "fadewhite",
    "wipe": "wiperight",
    "wipeleft": "wipelleft",
    "wiperight": "wiperight",
    "slide": "slideright",
    "slideleft": "slideleft",
    "slideright": "slideright",
    "circleopen": "circleopen",
    "circleclose": "circleclose",
    "dissolve": "dissolve",
    "radial": "radial",
    "smoothleft": "smoothleft",
    "smoothright": "smoothright",
    "smoothup": "smoothup",
    "smoothdown": "smoothdown",
}

ANCHOR_MAP = {
    "top_left": ("0", "0"),
    "top_center": ("(w-text_w)/2", "0"),
    "top_right": ("(w-text_w)", "0"),
    "center_left": ("0", "(h-text_h)/2"),
    "center": ("(w-text_w)/2", "(h-text_h)/2"),
    "center_right": ("(w-text_w)", "(h-text_h)/2"),
    "bottom_left": ("0", "(h-text_h)"),
    "bottom_center": ("(w-text_w)/2", "(h-text_h)"),
    "bottom_right": ("(w-text_w)", "(h-text_h)"),
}

DEFAULT_FONT_PATHS = {
    "Arial": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "arial": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "Helvetica": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "sans-serif": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "DejaVu Sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "Roboto": "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
    "Noto Sans": "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
}

FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


class CompositionError(Exception):
    pass


class SegmentValidationError(CompositionError):
    pass


@dataclass
class OverlaySpec:
    text: str
    font_size: int = 48
    font_color: str = "#FFFFFF"
    stroke_color: str = "#000000"
    stroke_width: int = 2
    font_family: str = "Arial"
    x: str | int | float = "(w-text_w)/2"
    y: str | int | float = "(h-text_h)/2"
    anchor: str = "center"
    start_time: float = 0.0
    end_time: float = 10.0
    animation: str = "none"

    def resolve_position(self) -> tuple[str, str]:
        has_explicit_x = not isinstance(self.x, str) or self.x != "(w-text_w)/2"
        has_explicit_y = not isinstance(self.y, str) or self.y != "(h-text_h)/2"
        numeric_x = isinstance(self.x, (int, float))
        numeric_y = isinstance(self.y, (int, float))
        if (numeric_x or numeric_y) and self.anchor == "center":
            x_val = str(self.x) if numeric_x else self.x
            y_val = str(self.y) if numeric_y else self.y
            return x_val, y_val
        if self.anchor in ANCHOR_MAP:
            return ANCHOR_MAP[self.anchor]
        x_val = str(self.x) if numeric_x else self.x
        y_val = str(self.y) if numeric_y else self.y
        return x_val, y_val

    def resolve_font_path(self) -> str:
        custom_path = SETTINGS.ffmpeg_path if hasattr(SETTINGS, "font_dir") else ""
        if custom_path and os.path.exists(custom_path):
            return custom_path
        mapped = DEFAULT_FONT_PATHS.get(self.font_family)
        if mapped and os.path.exists(mapped):
            return mapped
        if os.path.exists(FALLBACK_FONT):
            return FALLBACK_FONT
        return self.font_family


@dataclass
class SegmentSpec:
    video_path: str
    duration: float | None = None
    tts_path: str | None = None
    tts_volume: float = 1.0
    transition: str = "fade"
    transition_duration: float = 1.0
    overlays: list[OverlaySpec] = field(default_factory=list)
    fade_in: float = 0.0
    fade_out: float = 0.0


@dataclass
class CompositionResult:
    output_path: str
    final_duration: float
    segments_composed: int
    overlays_applied: int
    audio_tracks: int
    warnings: list[str] = field(default_factory=list)


async def probe_duration(file_path: str) -> float:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    loop = asyncio.get_event_loop()

    def _probe():
        raw = ffmpeg.probe(file_path)
        dur = raw.get("format", {}).get("duration")
        if dur is not None:
            return float(dur)
        for stream in raw.get("streams", []):
            if "duration" in stream:
                return float(stream["duration"])
        return 0.0

    return await loop.run_in_executor(None, _probe)


async def get_video_info(file_path: str) -> dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    loop = asyncio.get_event_loop()

    def _probe():
        raw = ffmpeg.probe(file_path)
        video_stream = next((s for s in raw["streams"] if s["codec_type"] == "video"), None)
        audio_stream = next((s for s in raw["streams"] if s["codec_type"] == "audio"), None)
        fps = None
        if video_stream and "r_frame_rate" in video_stream:
            parts = video_stream["r_frame_rate"].split("/")
            if len(parts) == 2 and int(parts[1]) != 0:
                fps = int(parts[0]) / int(parts[1])
        return {
            "duration": float(raw["format"].get("duration", 0)),
            "width": int(video_stream["width"]) if video_stream else None,
            "height": int(video_stream["height"]) if video_stream else None,
            "has_audio": audio_stream is not None,
            "fps": fps,
            "codec": video_stream.get("codec_name") if video_stream else None,
        }

    return await loop.run_in_executor(None, _probe)


async def _run_ffmpeg(cmd, timeout: int = 600) -> None:
    loop = asyncio.get_event_loop()

    def _exec():
        cmd.overwrite_output().run(capture_stdout=True, capture_stderr=True)

    await asyncio.wait_for(loop.run_in_executor(None, _exec), timeout=timeout)


async def _run_ffmpeg_raw(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    result = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=timeout)
    if result.returncode != 0:
        raise CompositionError(f"FFmpeg command failed (code {result.returncode}): {stderr.decode()[:500]}")
    return subprocess.CompletedProcess(args, result.returncode, stdout, stderr)


async def _copy_file(src: str, dst: str) -> str:
    loop = asyncio.get_event_loop()
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    await loop.run_in_executor(None, shutil.copy2, src, dst)
    return dst


def _resolve_transition(name: str) -> str:
    return TRANSITION_TYPES.get(name, TRANSITION_TYPES.get("fade", "fade"))


def validate_segments(segments: list[SegmentSpec]) -> list[str]:
    errors: list[str] = []
    if not segments:
        errors.append("No segments provided")
        return errors
    missing = [s.video_path for s in segments if not os.path.exists(s.video_path)]
    if missing:
        errors.append(f"Missing video files: {missing}")
    for i, seg in enumerate(segments):
        if seg.tts_path and not os.path.exists(seg.tts_path):
            errors.append(f"Segment {i}: TTS file missing: {seg.tts_path}")
        if seg.fade_in < 0 or seg.fade_out < 0:
            errors.append(f"Segment {i}: fade durations must be >= 0")
        if seg.transition_duration < 0:
            errors.append(f"Segment {i}: transition duration must be >= 0")
    return errors


async def concatenate_videos_with_transitions(
    input_paths: list[str],
    output_path: str,
    transitions: list[str] | None = None,
    fade_duration: float = 1.0,
    segment_durations: list[float] | None = None,
) -> str:
    if not input_paths:
        raise CompositionError("No input files provided")

    if len(input_paths) == 1:
        return await _copy_file(input_paths[0], output_path)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if transitions is None:
        transitions = ["fade"] * (len(input_paths) - 1)

    durations = segment_durations
    if durations is None:
        durations = []
        for p in input_paths:
            try:
                durations.append(await probe_duration(p))
            except Exception:
                durations.append(10.0)

    if len(input_paths) == 2:
        return await _xfade_two(
            input_paths, output_path,
            _resolve_transition(transitions[0]),
            fade_duration,
            durations,
        )

    return await _xfade_chain(
        input_paths, output_path,
        [_resolve_transition(t) for t in transitions],
        fade_duration,
        durations,
    )


async def _xfade_two(
    input_paths: list[str],
    output_path: str,
    transition: str,
    fade_duration: float,
    durations: list[float],
) -> str:
    v0_dur = durations[0]
    offset = max(v0_dur - fade_duration, 0)

    inp0 = ffmpeg.input(input_paths[0])
    inp1 = ffmpeg.input(input_paths[1])

    xfade_video = ffmpeg.filter(
        [inp0.video, inp1.video],
        "xfade",
        transition=transition,
        duration=fade_duration,
        offset=offset,
    )

    a0 = inp0.audio if _has_audio(input_paths[0]) else _silent_audio(fade_duration)
    a1 = inp1.audio if _has_audio(input_paths[1]) else _silent_audio(fade_duration)

    acrossfade = ffmpeg.filter(
        [a0, a1],
        "acrossfade",
        d=fade_duration,
        c1="tri",
        c2="tri",
    )

    merged = ffmpeg.concat(xfade_video, acrossfade, a=1)

    await _run_ffmpeg(
        merged.output(
            output_path,
            vcodec="libx264",
            acodec="aac",
            crf=18,
            preset="fast",
            pix_fmt="yuv420p",
            movflags="+faststart",
            **{"b:a": "192k"},
        ),
    )
    logger.info(f"Two-clip xfade saved to {output_path}")
    return output_path


async def _xfade_chain(
    input_paths: list[str],
    output_path: str,
    transitions: list[str],
    fade_duration: float,
    durations: list[float],
) -> str:
    inputs = [ffmpeg.input(p) for p in input_paths]

    current_video = inputs[0].video
    current_audio = inputs[0].audio if _has_audio(input_paths[0]) else _silent_audio(durations[0])
    accumulated_duration = durations[0]

    for i in range(1, len(inputs)):
        trans_name = transitions[i - 1] if i - 1 < len(transitions) else "fade"
        fd = fade_duration if i - 1 < len(transitions) else fade_duration
        offset = max(accumulated_duration - fd, 0)

        next_video = inputs[i].video
        next_audio = inputs[i].audio if _has_audio(input_paths[i]) else _silent_audio(durations[i])

        current_video = ffmpeg.filter(
            [current_video, next_video],
            "xfade",
            transition=trans_name,
            duration=fd,
            offset=int(offset * 100) / 100,
        )

        current_audio = ffmpeg.filter(
            [current_audio, next_audio],
            "acrossfade",
            d=fd,
            c1="tri",
            c2="tri",
        )

        accumulated_duration = offset + fd + durations[i]

    merged = ffmpeg.concat(current_video, current_audio, a=1)

    await _run_ffmpeg(
        merged.output(
            output_path,
            vcodec="libx264",
            acodec="aac",
            crf=18,
            preset="fast",
            pix_fmt="yuv420p",
            movflags="+faststart",
            **{"b:a": "192k"},
        ),
    )
    logger.info(f"N-clip xfade chain saved to {output_path} ({len(input_paths)} segments)")
    return output_path


def _has_audio(file_path: str) -> bool:
    try:
        probe = ffmpeg.probe(file_path)
        return any(s["codec_type"] == "audio" for s in probe.get("streams", []))
    except Exception:
        return False


def _silent_audio(duration: float, sample_rate: int = 44100):
    return ffmpeg.input(f"anullsrc=r={sample_rate}", f="lavfi", t=duration).audio


async def apply_fade_in_out(
    input_path: str,
    output_path: str,
    fade_in_duration: float = 0.5,
    fade_out_duration: float = 0.5,
) -> str:
    duration = await probe_duration(input_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    inp = ffmpeg.input(input_path)
    video = inp.video
    audio = inp.audio

    if fade_in_duration > 0:
        video = video.filter("fade", type="in", start_time=0, duration=fade_in_duration)
        audio = audio.filter("afade", type="in", start_time=0, duration=fade_in_duration)

    if fade_out_duration > 0 and duration > fade_out_duration:
        fade_start = duration - fade_out_duration
        video = video.filter("fade", type="out", start_time=fade_start, duration=fade_out_duration)
        audio = audio.filter("afade", type="out", start_time=fade_start, duration=fade_out_duration)

    merged = ffmpeg.concat(video, audio, a=1) if _has_audio(input_path) else video

    await _run_ffmpeg(
        merged.output(
            output_path,
            vcodec="libx264",
            acodec="aac",
            crf=18,
            preset="fast",
            pix_fmt="yuv420p",
            movflags="+faststart",
        ),
    )
    logger.info(f"Fade in/out applied, saved to {output_path}")
    return output_path


async def add_text_overlay(
    input_path: str,
    output_path: str,
    overlays: list[dict | OverlaySpec],
    width: int = 1080,
    height: int = 1920,
) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    resolved = []
    for o in overlays:
        if isinstance(o, dict):
            o = OverlaySpec(
                text=o.get("text", ""),
                font_size=o.get("font_size", 48),
                font_color=o.get("color", o.get("font_color", "#FFFFFF")),
                stroke_color=o.get("stroke_color", "#000000"),
                stroke_width=o.get("stroke_width", 2),
                font_family=o.get("font_family", "Arial"),
                x=o.get("x", "(w-text_w)/2"),
                y=o.get("y", "(h-text_h)/2"),
                anchor=o.get("anchor", "center"),
                start_time=o.get("start_time", 0.0),
                end_time=o.get("end_time", 10.0),
                animation=o.get("animation", "none"),
            )
        resolved.append(o)

    inp = ffmpeg.input(input_path)
    stream = inp.video.filter("scale", width, height)

    needs_ass = _needs_ass_subtitle(resolved)
    if needs_ass:
        return await _add_ass_overlay(input_path, output_path, resolved, width, height)

    overlay_count = 0
    for overlay in resolved:
        text = (overlay.text or "").replace("'", "'").replace(":", "\\:")
        font_path = overlay.resolve_font_path()
        x_expr, y_expr = overlay.resolve_position()
        color_hex = overlay.font_color.lstrip("#")
        stroke_hex = overlay.stroke_color.lstrip("#")
        enable_expr = f"between(t,{overlay.start_time},{overlay.end_time})"

        drawtext_kwargs = {
            "text": text,
            "fontsize": overlay.font_size,
            "fontcolor": f"0x{color_hex}",
            "borderw": overlay.stroke_width,
            "bordercolor": f"0x{stroke_hex}",
            "x": x_expr,
            "y": y_expr,
            "enable": enable_expr,
        }

        if os.path.exists(font_path):
            drawtext_kwargs["fontfile"] = font_path

        stream = stream.drawtext(**drawtext_kwargs)
        overlay_count += 1

    audio = inp.audio
    out = ffmpeg.concat(stream, audio, a=1) if _has_audio(input_path) else stream

    await _run_ffmpeg(
        out.output(
            output_path,
            vcodec="libx264",
            acodec="aac",
            crf=18,
            preset="fast",
            pix_fmt="yuv420p",
            movflags="+faststart",
        ),
    )
    logger.info(f"Applied {overlay_count} drawtext overlays, saved to {output_path}")
    return output_path


def _needs_ass_subtitle(overlays: list[OverlaySpec]) -> bool:
    for o in overlays:
        if o.animation not in ("none", "fade"):
            return True
        text_lines = o.text.count("\n") + 1
        if text_lines > 2:
            return True
    return False


async def _add_ass_overlay(
    input_path: str,
    output_path: str,
    overlays: list[OverlaySpec],
    width: int = 1080,
    height: int = 1920,
) -> str:
    ass_content = _generate_ass_script(overlays, width, height)
    tmp_dir = tempfile.mkdtemp(prefix="ffmpeg_ass_")
    ass_path = os.path.join(tmp_dir, "overlays.ass")

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    try:
        inp = ffmpeg.input(input_path)
        video = inp.video.filter("scale", width, height)
        video = video.filter("subtitles", ass_path, force_style="")

        audio = inp.audio
        out = ffmpeg.concat(video, audio, a=1) if _has_audio(input_path) else video

        await _run_ffmpeg(
            out.output(
                output_path,
                vcodec="libx264",
                acodec="aac",
                crf=18,
                preset="fast",
                pix_fmt="yuv420p",
                movflags="+faststart",
            ),
        )
        logger.info(f"Applied {len(overlays)} ASS subtitle overlays, saved to {output_path}")
        return output_path
    finally:
        try:
            os.unlink(ass_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


def _generate_ass_script(overlays: list[OverlaySpec], width: int, height: int) -> str:
    play_res_x = width
    play_res_y = height

    styles = []
    events = []

    for i, o in enumerate(overlays):
        style_name = f"Overlay{i}"
        font_name = o.font_family
        font_size = o.font_size
        primary_col = _hex_to_ass_color(o.font_color)
        outline_col = _hex_to_ass_color(o.stroke_color)
        border_style = 1 if o.stroke_width > 0 else 0
        outline_width = o.stroke_width
        alignment = _anchor_to_ass_alignment(o.anchor)
        margin_v = 10

        styles.append(
            f"Style: {style_name},{font_name},{font_size},"
            f"&H00{primary_col},&H{primary_col},&H{outline_col},&H{outline_col},"
            f"{border_style},{outline_width},0,0,100,100,0,0,1,{alignment},"
            f"0,0,1,{margin_v},{margin_v},{margin_v},{margin_v}"
        )

        x_pos, y_pos = o.resolve_position()
        text = o.text.replace("\n", "\\N")
        start_time = _format_ass_time(o.start_time)
        end_time = _format_ass_time(o.end_time)

        if o.animation == "fade":
            fade_in_ms = 500
            fade_out_ms = 500
            start_fade_in = _format_ass_time(o.start_time)
            end_fade_in = _format_ass_time(o.start_time + fade_in_ms / 1000.0)
            start_fade_out = _format_ass_time(o.end_time - fade_out_ms / 1000.0)
            end_fade_out = _format_ass_time(o.end_time)

            events.append(
                f"Dialogue: 0,{start_time},{end_fade_in},{style_name},,0,0,0,,"
                f"{{\\fade(255,0,255,0)}}{text}"
            )
            events.append(
                f"Dialogue: 0,{end_fade_in},{start_fade_out},{style_name},,0,0,0,,"
                f"{{\\1a&H00&}}{text}"
            )
            events.append(
                f"Dialogue: 0,{start_fade_out},{end_time},{style_name},,0,0,0,,"
                f"{{\\fade(0,0,255,255)}}{text}"
            )
        else:
            events.append(
                f"Dialogue: 0,{start_time},{end_time},{style_name},,0,0,0,,"
                f"{{\\pos({x_pos},{y_pos})}}{text}"
            )

    ass = f"""[Script Info]
Title: Video Overlays
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, MarginV
{chr(10).join(styles)}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(events)}
"""
    return ass


def _hex_to_ass_color(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
        return f"B{b.upper()}{g.upper()}{r.upper()}"
    return "FFFFFF"


def _anchor_to_ass_alignment(anchor: str) -> int:
    alignment_map = {
        "top_left": 7,
        "top_center": 8,
        "top_right": 9,
        "center_left": 4,
        "center": 5,
        "center_right": 6,
        "bottom_left": 1,
        "bottom_center": 2,
        "bottom_right": 3,
    }
    return alignment_map.get(anchor, 5)


def _format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _normalize_segments(
    segments: list[SegmentSpec],
) -> tuple[list[str], list[str], list[str], list[OverlaySpec], list[float], list[dict]]:
    video_paths = []
    tts_paths = []
    transitions = []
    all_overlays = []
    durations = []
    tts_volumes = []

    for seg in segments:
        video_paths.append(seg.video_path)
        if seg.tts_path:
            tts_paths.append(seg.tts_path)
        transitions.append(seg.transition)
        durations.append(seg.duration or 10.0)
        all_overlays.extend(seg.overlays)
        tts_volumes.append(seg.tts_volume)

    return video_paths, tts_paths, transitions, all_overlays, durations, tts_volumes


async def mix_audio_with_tts(
    video_path: str,
    tts_segments: list[str],
    bgm_path: str | None,
    output_path: str,
    tts_volumes: list[float] | None = None,
    bgm_volume: float = 0.2,
    segment_durations: list[float] | None = None,
    enable_sidechain_ducking: bool = True,
    fade_out_seconds: float = 2.0,
) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    video = ffmpeg.input(video_path)
    video_stream = video.video.filter("scale", 1080, 1920)
    video_duration = await probe_duration(video_path)

    tts_inputs = []
    for i, tts_path in enumerate(tts_segments):
        if not os.path.exists(tts_path):
            logger.warning(f"TTS file missing, skipping: {tts_path}")
            continue
        vol = (tts_volumes or [1.0] * len(tts_segments))[i] if tts_volumes and i < len(tts_volumes) else 1.0
        tts_stream = ffmpeg.input(tts_path).audio.filter("volume", vol)

        if segment_durations and i < len(segment_durations):
            target_dur = segment_durations[i]
            actual_dur = await probe_duration(tts_path)
            if actual_dur > 0 and actual_dur < target_dur:
                tts_stream = tts_stream.filter("apad", whole_dur=target_dur)
            elif actual_dur > target_dur * 1.1:
                tts_stream = tts_stream.filter("atrim", end=target_dur).filter("asetpts", "PTS-STARTPTS")

        tts_inputs.append(tts_stream)

    if not tts_inputs and not bgm_path:
        out = ffmpeg.concat(video_stream, video.audio if _has_audio(video_path) else _silent_audio(video_duration), a=1)
        await _run_ffmpeg(
            out.output(
                output_path,
                vcodec="libx264",
                acodec="aac",
                crf=18,
                preset="fast",
                pix_fmt="yuv420p",
                movflags="+faststart",
                **{"b:a": "192k"},
            ),
        )
        return output_path

    all_audio = list(tts_inputs)

    if bgm_path and os.path.exists(bgm_path):
        bgm_audio = ffmpeg.input(bgm_path).audio.filter("volume", bgm_volume)
        bgm_dur = await probe_duration(bgm_path)

        if bgm_dur < video_duration:
            bgm_audio = bgm_audio.filter("apad", whole_dur=video_duration)
        elif bgm_dur > video_duration + 5:
            bgm_audio = bgm_audio.filter("atrim", end=video_duration).filter("asetpts", "PTS-STARTPTS")

        if enable_sidechain_ducking and tts_inputs:
            bgm_loud = bgm_audio.filter("volume", bgm_volume * 2)

            mixed_tts = tts_inputs[0]
            for ts in tts_inputs[1:]:
                mixed_tts = ffmpeg.filter([mixed_tts, ts], "amix", inputs=2, duration="longest")

            ducked_bgm = ffmpeg.filter(
                [bgm_loud, mixed_tts],
                "sidechaincompress",
                threshold="-20dB",
                ratio=6,
                attack=5,
                release=50,
            )

            all_audio = [mixed_tts, ducked_bgm]
        else:
            all_audio.append(bgm_audio)

    if len(all_audio) == 1:
        mixed = all_audio[0]
    elif len(all_audio) == 2:
        mixed = ffmpeg.filter(all_audio, "amix", inputs=2, duration="longest", dropout_transition=2)
    else:
        mixed = all_audio[0]
        for a in all_audio[1:]:
            mixed = ffmpeg.filter([mixed, a], "amix", inputs=2, duration="longest", dropout_transition=2)

    if fade_out_seconds > 0 and video_duration > fade_out_seconds:
        mixed = mixed.filter("afade", type="out", start_time=video_duration - fade_out_seconds, duration=fade_out_seconds)

    out = ffmpeg.concat(video_stream, mixed, a=1)

    await _run_ffmpeg(
        out.output(
            output_path,
            vcodec="libx264",
            acodec="aac",
            crf=18,
            preset="fast",
            pix_fmt="yuv420p",
            movflags="+faststart",
            **{"b:a": "192k"},
        ),
    )
    logger.info(f"Audio mix complete (ducking={enable_sidechain_ducking}, {len(tts_inputs)} TTS, BGM={'yes' if bgm_path else 'no'}), saved to {output_path}")
    return output_path


async def extend_audio_to_duration(
    audio_path: str,
    target_duration: float,
    output_path: str | None = None,
) -> str:
    if output_path is None:
        output_path = audio_path.replace(".mp3", "_padded.mp3").replace(".wav", "_padded.wav").replace(".m4a", "_padded.m4a")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if not os.path.exists(audio_path):
        raise CompositionError(f"Audio file not found: {audio_path}")

    actual_duration = await probe_duration(audio_path)
    if actual_duration <= 0:
        raise CompositionError(f"Could not determine duration of {audio_path}")

    if actual_duration >= target_duration:
        return await _copy_file(audio_path, output_path)

    try:
        inp = ffmpeg.input(audio_path)
        await _run_ffmpeg(
            inp.output(
                output_path,
                af=f"apad=whole_dur={target_duration:.3f}",
                acodec="aac",
                **{"b:a": "192k"},
            ),
        )
        logger.info(f"Extended audio {audio_path} from {actual_duration:.2f}s to {target_duration:.2f}s")
        return output_path
    except Exception as e:
        logger.warning(f"Could not extend audio with apad: {e}")
        return audio_path


async def measure_audio_sync_drift(
    video_path: str,
    tts_path: str,
) -> tuple[float, float]:
    video_duration = await probe_duration(video_path)
    tts_duration = await probe_duration(tts_path)
    drift = tts_duration - video_duration
    offset_ms = abs(drift) * 1000
    return drift, offset_ms


async def combine_audio_streams(
    tts_path: str,
    bgm_path: str,
    output_path: str,
    tts_volume: float = 1.0,
    bgm_volume: float = 0.5,
    fade_out_seconds: float = 2.0,
) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    tts_audio = ffmpeg.input(tts_path).audio.filter("volume", tts_volume)
    bgm_audio = ffmpeg.input(bgm_path).audio.filter("volume", bgm_volume)

    tts_dur = await probe_duration(tts_path)
    bgm_dur = await probe_duration(bgm_path)

    if bgm_dur < tts_dur:
        bgm_audio = bgm_audio.filter("apad", whole_dur=tts_dur)

    mixed = ffmpeg.filter([tts_audio, bgm_audio], "amix", inputs=2, duration="longest")

    if fade_out_seconds > 0 and tts_dur > fade_out_seconds:
        fade_start = tts_dur - fade_out_seconds
        mixed = mixed.filter("afade", type="out", start_time=fade_start, duration=fade_out_seconds)

    await _run_ffmpeg(
        mixed.output(
            output_path,
            acodec="aac",
            **{"b:a": "192k"},
        ),
    )
    logger.info(f"Combined audio streams saved to {output_path}")
    return output_path


async def export_final_video(
    segments: list[SegmentSpec] | None = None,
    input_segments: list[str] | None = None,
    text_overlays: list[dict] | None = None,
    tts_segments: list[str] | None = None,
    bgm_path: str | None = None,
    output_path: str | None = None,
    transitions: list[str] | None = None,
    width: int = 1080,
    height: int = 1920,
    fade_duration: float = 1.0,
    segment_actual_durations: list[float] | None = None,
    enable_sidechain_ducking: bool = True,
    fade_in_duration: float = 0.0,
    fade_out_duration: float = 0.0,
) -> CompositionResult:
    tmp_dir = os.path.join(SETTINGS.output_dir, "tmp", str(uuid.uuid4()))
    os.makedirs(tmp_dir, exist_ok=True)
    warnings: list[str] = []
    overlay_count = 0

    try:
        if segments:
            spec = segments
        elif input_segments:
            spec = []
            for i, path in enumerate(input_segments):
                overlay_list = []
                if text_overlays:
                    overlay_list = [OverlaySpec(**o) if isinstance(o, dict) else o for o in text_overlays]
                trans = "fade"
                if transitions and i < len(transitions):
                    trans = transitions[i]
                spec.append(SegmentSpec(
                    video_path=path,
                    duration=segment_actual_durations[i] if segment_actual_durations and i < len(segment_actual_durations) else None,
                    tts_path=tts_segments[i] if tts_segments and i < len(tts_segments) else None,
                    transition=trans,
                    transition_duration=fade_duration,
                    overlays=overlay_list,
                ))
        else:
            raise CompositionError("Either segments or input_segments must be provided")

        errors = validate_segments(spec)
        for e in errors:
            if "Missing video files" in e:
                raise SegmentValidationError(e)
            warnings.append(e)

        dur_list = []
        for s in spec:
            if s.duration:
                dur_list.append(s.duration)
            else:
                try:
                    dur_list.append(await probe_duration(s.video_path))
                except Exception:
                    dur_list.append(10.0)
                    warnings.append(f"Could not probe duration for {s.video_path}, using 10.0s")

        concat_path = os.path.join(tmp_dir, "concat.mp4")
        if len(spec) == 1:
            await _copy_file(spec[0].video_path, concat_path)
        else:
            await concatenate_videos_with_transitions(
                [s.video_path for s in spec],
                concat_path,
                transitions=[s.transition for s in spec[1:]],
                fade_duration=fade_duration,
                segment_durations=dur_list,
            )

        if fade_in_duration > 0 or fade_out_duration > 0:
            faded_path = os.path.join(tmp_dir, "faded.mp4")
            await apply_fade_in_out(concat_path, faded_path, fade_in_duration, fade_out_duration)
            concat_path = faded_path

        overlay_path = os.path.join(tmp_dir, "overlay.mp4")
        all_overlays = []
        global_time_offset = 0.0
        for seg_idx, seg in enumerate(spec):
            for overlay in seg.overlays:
                shifted = OverlaySpec(
                    text=overlay.text,
                    font_size=overlay.font_size,
                    font_color=overlay.font_color,
                    stroke_color=overlay.stroke_color,
                    stroke_width=overlay.stroke_width,
                    font_family=overlay.font_family,
                    x=overlay.x,
                    y=overlay.y,
                    anchor=overlay.anchor,
                    start_time=overlay.start_time + global_time_offset,
                    end_time=overlay.end_time + global_time_offset,
                    animation=overlay.animation,
                )
                all_overlays.append(shifted)
            global_time_offset += dur_list[seg_idx] - (fade_duration if seg_idx > 0 else 0)

        if all_overlays:
            await add_text_overlay(concat_path, overlay_path, all_overlays, width=width, height=height)
            overlay_count = len(all_overlays)
        else:
            await _copy_file(concat_path, overlay_path)

        final_path = os.path.join(tmp_dir, "final.mp4")
        collected_tts = [s.tts_path for s in spec if s.tts_path]
        tts_vols = [s.tts_volume for s in spec if s.tts_path]

        if collected_tts or bgm_path:
            await mix_audio_with_tts(
                overlay_path,
                collected_tts if collected_tts else [],
                bgm_path,
                final_path,
                tts_volumes=tts_vols,
                segment_durations=dur_list,
                enable_sidechain_ducking=enable_sidechain_ducking,
            )
        else:
            scaled_path = os.path.join(tmp_dir, "scaled.mp4")
            inp = ffmpeg.input(overlay_path)
            video = inp.video.filter("scale", width, height)
            if _has_audio(overlay_path):
                audio = inp.audio
                out = ffmpeg.concat(video, audio, a=1)
            else:
                audio = _silent_audio(await probe_duration(overlay_path))
                out = ffmpeg.concat(video, audio, a=1)

            await _run_ffmpeg(
                out.output(
                    scaled_path,
                    vcodec="libx264",
                    acodec="aac",
                    crf=18,
                    preset="fast",
                    pix_fmt="yuv420p",
                    movflags="+faststart",
                    **{"b:a": "192k"},
                ),
            )
            final_path = scaled_path

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            await _copy_file(final_path, output_path)
        else:
            output_path = final_path

        total_duration = sum(dur_list) - (fade_duration * max(0, len(spec) - 1))

        return CompositionResult(
            output_path=output_path,
            final_duration=total_duration,
            segments_composed=len(spec),
            overlays_applied=overlay_count,
            audio_tracks=len(collected_tts) + (1 if bgm_path else 0),
            warnings=warnings,
        )
    finally:
        if output_path and not output_path.startswith(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except Exception:
                pass