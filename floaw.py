#!/usr/bin/env python3
"""FLOAW - A watermark-free video editor CLI powered by FFmpeg.

This tool offers a broad set of day-to-day editing features:
- Trim / cut
- Concatenate multiple clips
- Resize, crop, rotate, flip
- Speed controls (video and audio)
- Brightness / contrast / saturation
- Blur / sharpen / grayscale
- Text and image overlays
- Fade in/out (video and audio)
- Audio replacement, mute, and volume controls
- Frame-rate and codec/quality controls
- Export to MP4/MOV/MKV/WEBM (any FFmpeg-supported format)

No watermark is ever added by this software.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class EditConfig:
    inputs: List[Path]
    output: Path
    start: Optional[float]
    end: Optional[float]
    duration: Optional[float]
    width: Optional[int]
    height: Optional[int]
    crop: Optional[str]
    rotate: Optional[int]
    hflip: bool
    vflip: bool
    speed: Optional[float]
    fps: Optional[int]
    brightness: Optional[float]
    contrast: Optional[float]
    saturation: Optional[float]
    blur: Optional[float]
    sharpen: bool
    grayscale: bool
    text: Optional[str]
    text_x: str
    text_y: str
    text_size: int
    text_color: str
    font: Optional[Path]
    image_overlay: Optional[Path]
    image_x: str
    image_y: str
    image_scale: Optional[str]
    fade_in: Optional[float]
    fade_out: Optional[float]
    afade_in: Optional[float]
    afade_out: Optional[float]
    mute: bool
    audio_file: Optional[Path]
    audio_volume: Optional[float]
    replace_audio: bool
    video_codec: str
    audio_codec: str
    crf: int
    preset: str
    threads: Optional[int]
    overwrite: bool


def parse_args() -> EditConfig:
    parser = argparse.ArgumentParser(
        prog="floaw",
        description="Feature-rich, watermark-free video editing CLI.",
    )

    parser.add_argument("inputs", nargs="+", type=Path, help="Input video file(s).")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output file path.")

    parser.add_argument("--start", type=float, help="Trim start time (seconds).")
    parser.add_argument("--end", type=float, help="Trim end time (seconds).")
    parser.add_argument("--duration", type=float, help="Trim duration (seconds).")

    parser.add_argument("--width", type=int, help="Output width.")
    parser.add_argument("--height", type=int, help="Output height.")
    parser.add_argument("--crop", help="Crop as w:h:x:y (example: 1280:720:0:0).")

    parser.add_argument("--rotate", type=int, choices=[90, 180, 270], help="Rotate video.")
    parser.add_argument("--hflip", action="store_true", help="Flip horizontally.")
    parser.add_argument("--vflip", action="store_true", help="Flip vertically.")

    parser.add_argument("--speed", type=float, help="Playback speed multiplier (e.g., 0.5, 1.5, 2.0).")
    parser.add_argument("--fps", type=int, help="Set output frames per second.")

    parser.add_argument("--brightness", type=float, help="Brightness adjustment (typically -1.0 to 1.0).")
    parser.add_argument("--contrast", type=float, help="Contrast multiplier (typically 0.5 to 2.0).")
    parser.add_argument("--saturation", type=float, help="Saturation multiplier (typically 0.0 to 3.0).")
    parser.add_argument("--blur", type=float, help="Gaussian blur sigma amount.")
    parser.add_argument("--sharpen", action="store_true", help="Apply sharpening filter.")
    parser.add_argument("--grayscale", action="store_true", help="Convert to grayscale.")

    parser.add_argument("--text", help="Add text overlay.")
    parser.add_argument("--text-x", default="(w-text_w)/2", help="Text X position expression.")
    parser.add_argument("--text-y", default="h-(text_h*2)", help="Text Y position expression.")
    parser.add_argument("--text-size", type=int, default=48, help="Text size.")
    parser.add_argument("--text-color", default="white", help="Text color.")
    parser.add_argument("--font", type=Path, help="Path to .ttf/.otf font file.")

    parser.add_argument("--image-overlay", type=Path, help="Overlay image path.")
    parser.add_argument("--image-x", default="20", help="Image overlay X expression.")
    parser.add_argument("--image-y", default="20", help="Image overlay Y expression.")
    parser.add_argument("--image-scale", help="Scale image overlay as w:h (example: 200:-1).")

    parser.add_argument("--fade-in", type=float, help="Video fade in duration in seconds.")
    parser.add_argument("--fade-out", type=float, help="Video fade out duration in seconds (from end).")
    parser.add_argument("--afade-in", type=float, help="Audio fade in duration in seconds.")
    parser.add_argument("--afade-out", type=float, help="Audio fade out duration in seconds (from end).")

    parser.add_argument("--mute", action="store_true", help="Remove audio from output.")
    parser.add_argument("--audio-file", type=Path, help="Optional external audio file for mix or replacement.")
    parser.add_argument("--audio-volume", type=float, help="Volume multiplier for output audio.")
    parser.add_argument("--replace-audio", action="store_true", help="Replace input audio with --audio-file.")

    parser.add_argument("--video-codec", default="libx264", help="Output video codec.")
    parser.add_argument("--audio-codec", default="aac", help="Output audio codec.")
    parser.add_argument("--crf", type=int, default=20, help="CRF quality (lower is higher quality).")
    parser.add_argument("--preset", default="medium", help="Encoder preset (ultrafast..veryslow).")
    parser.add_argument("--threads", type=int, help="Number of FFmpeg threads.")

    parser.add_argument("--overwrite", action="store_true", help="Overwrite output file if it exists.")

    args = parser.parse_args()

    if args.start is not None and args.start < 0:
        parser.error("--start must be >= 0")
    if args.end is not None and args.end < 0:
        parser.error("--end must be >= 0")
    if args.duration is not None and args.duration <= 0:
        parser.error("--duration must be > 0")
    if args.end is not None and args.start is not None and args.end <= args.start:
        parser.error("--end must be greater than --start")
    if args.speed is not None and args.speed <= 0:
        parser.error("--speed must be > 0")
    if args.audio_file is None and args.replace_audio:
        parser.error("--replace-audio requires --audio-file")

    return EditConfig(**vars(args))


def ffprobe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def speed_audio_chain(speed: float) -> str:
    # atempo supports 0.5..2.0 per stage
    chain: List[str] = []
    remaining = speed
    while remaining > 2.0:
        chain.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        chain.append("atempo=0.5")
        remaining /= 0.5
    chain.append(f"atempo={remaining:.5f}")
    return ",".join(chain)


def build_filter_complex(cfg: EditConfig, has_audio: bool) -> tuple[str, str, Optional[str], List[str]]:
    parts: List[str] = []
    current_v = "[0:v]"
    current_a = "[0:a]" if has_audio else None
    extra_inputs: List[str] = []

    if len(cfg.inputs) > 1:
        concat_in = "".join([f"[{i}:v][{i}:a]" for i in range(len(cfg.inputs))])
        parts.append(f"{concat_in}concat=n={len(cfg.inputs)}:v=1:a=1[vcat][acat]")
        current_v = "[vcat]"
        current_a = "[acat]"

    if cfg.width or cfg.height:
        w = cfg.width if cfg.width else -2
        h = cfg.height if cfg.height else -2
        parts.append(f"{current_v}scale={w}:{h}[vscale]")
        current_v = "[vscale]"

    if cfg.crop:
        parts.append(f"{current_v}crop={cfg.crop}[vcrop]")
        current_v = "[vcrop]"

    if cfg.rotate == 90:
        parts.append(f"{current_v}transpose=1[vrot]")
        current_v = "[vrot]"
    elif cfg.rotate == 180:
        parts.append(f"{current_v}transpose=1,transpose=1[vrot]")
        current_v = "[vrot]"
    elif cfg.rotate == 270:
        parts.append(f"{current_v}transpose=2[vrot]")
        current_v = "[vrot]"

    if cfg.hflip:
        parts.append(f"{current_v}hflip[vhflip]")
        current_v = "[vhflip]"
    if cfg.vflip:
        parts.append(f"{current_v}vflip[vvflip]")
        current_v = "[vvflip]"

    eq_params = []
    if cfg.brightness is not None:
        eq_params.append(f"brightness={cfg.brightness}")
    if cfg.contrast is not None:
        eq_params.append(f"contrast={cfg.contrast}")
    if cfg.saturation is not None:
        eq_params.append(f"saturation={cfg.saturation}")
    if eq_params:
        parts.append(f"{current_v}eq={':'.join(eq_params)}[veq]")
        current_v = "[veq]"

    if cfg.blur is not None:
        parts.append(f"{current_v}gblur=sigma={cfg.blur}[vblur]")
        current_v = "[vblur]"

    if cfg.sharpen:
        parts.append(f"{current_v}unsharp=5:5:1.0:5:5:0.0[vsharp]")
        current_v = "[vsharp]"

    if cfg.grayscale:
        parts.append(f"{current_v}hue=s=0[vgray]")
        current_v = "[vgray]"

    if cfg.speed is not None and cfg.speed != 1.0:
        parts.append(f"{current_v}setpts=PTS/{cfg.speed}[vspeed]")
        current_v = "[vspeed]"
        if current_a:
            atempo_chain = speed_audio_chain(cfg.speed)
            parts.append(f"{current_a}{atempo_chain}[aspeed]")
            current_a = "[aspeed]"

    if cfg.fps:
        parts.append(f"{current_v}fps={cfg.fps}[vfps]")
        current_v = "[vfps]"

    if cfg.text:
        escaped_text = cfg.text.replace("'", r"\'").replace(":", r"\:")
        draw = (
            f"drawtext=text='{escaped_text}':x={cfg.text_x}:y={cfg.text_y}:"
            f"fontsize={cfg.text_size}:fontcolor={cfg.text_color}"
        )
        if cfg.font:
            draw += f":fontfile={cfg.font}"
        parts.append(f"{current_v}{draw}[vtext]")
        current_v = "[vtext]"

    if cfg.image_overlay:
        # add image as extra input index len(inputs)
        image_idx = len(cfg.inputs)
        extra_inputs.extend(["-i", str(cfg.image_overlay)])
        source = f"[{image_idx}:v]"
        if cfg.image_scale:
            parts.append(f"{source}scale={cfg.image_scale}[ovrscaled]")
            source = "[ovrscaled]"
        parts.append(f"{current_v}{source}overlay={cfg.image_x}:{cfg.image_y}[vovr]")
        current_v = "[vovr]"

    if cfg.fade_in:
        parts.append(f"{current_v}fade=t=in:st=0:d={cfg.fade_in}[vfadein]")
        current_v = "[vfadein]"

    if cfg.fade_out:
        duration = ffprobe_duration(cfg.inputs[0])
        if cfg.start:
            duration -= cfg.start
        if cfg.end:
            duration = cfg.end - (cfg.start or 0)
        if cfg.duration:
            duration = cfg.duration
        st = max(duration - cfg.fade_out, 0.0)
        parts.append(f"{current_v}fade=t=out:st={st:.3f}:d={cfg.fade_out}[vfadeout]")
        current_v = "[vfadeout]"

    if cfg.audio_file:
        audio_idx = len(cfg.inputs) + (1 if cfg.image_overlay else 0)
        extra_inputs.extend(["-i", str(cfg.audio_file)])
        if cfg.replace_audio or not current_a:
            current_a = f"[{audio_idx}:a]"
        else:
            parts.append(f"{current_a}[{audio_idx}:a]amix=inputs=2:duration=first:dropout_transition=2[amixed]")
            current_a = "[amixed]"

    if current_a and cfg.audio_volume is not None:
        parts.append(f"{current_a}volume={cfg.audio_volume}[avol]")
        current_a = "[avol]"

    if current_a and cfg.afade_in:
        parts.append(f"{current_a}afade=t=in:st=0:d={cfg.afade_in}[afadein]")
        current_a = "[afadein]"

    if current_a and cfg.afade_out:
        duration = ffprobe_duration(cfg.inputs[0])
        if cfg.start:
            duration -= cfg.start
        if cfg.end:
            duration = cfg.end - (cfg.start or 0)
        if cfg.duration:
            duration = cfg.duration
        st = max(duration - cfg.afade_out, 0.0)
        parts.append(f"{current_a}afade=t=out:st={st:.3f}:d={cfg.afade_out}[afadeout]")
        current_a = "[afadeout]"

    return ";".join(parts), current_v, current_a, extra_inputs


def has_audio_stream(path: Path) -> bool:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "csv=p=0",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return bool(result.stdout.strip())


def run(cfg: EditConfig) -> int:
    for p in cfg.inputs:
        if not p.exists():
            print(f"Input file not found: {p}", file=sys.stderr)
            return 1

    if cfg.audio_file and not cfg.audio_file.exists():
        print(f"Audio file not found: {cfg.audio_file}", file=sys.stderr)
        return 1

    if cfg.image_overlay and not cfg.image_overlay.exists():
        print(f"Overlay image not found: {cfg.image_overlay}", file=sys.stderr)
        return 1

    output_parent = cfg.output.parent
    if output_parent and not output_parent.exists():
        output_parent.mkdir(parents=True, exist_ok=True)

    has_audio = has_audio_stream(cfg.inputs[0])

    cmd = ["ffmpeg"]
    cmd.append("-y" if cfg.overwrite else "-n")

    if cfg.start is not None:
        cmd += ["-ss", str(cfg.start)]

    for p in cfg.inputs:
        cmd += ["-i", str(p)]

    if cfg.end is not None:
        cmd += ["-to", str(cfg.end)]
    if cfg.duration is not None:
        cmd += ["-t", str(cfg.duration)]

    filter_complex, v_map, a_map, extra_inputs = build_filter_complex(cfg, has_audio)
    cmd += extra_inputs

    if filter_complex:
        cmd += ["-filter_complex", filter_complex, "-map", v_map]
        if not cfg.mute and a_map:
            cmd += ["-map", a_map]
    else:
        cmd += ["-map", "0:v:0"]
        if not cfg.mute and has_audio:
            cmd += ["-map", "0:a:0"]

    if cfg.mute:
        cmd += ["-an"]
    else:
        cmd += ["-c:a", cfg.audio_codec]

    cmd += [
        "-c:v",
        cfg.video_codec,
        "-crf",
        str(cfg.crf),
        "-preset",
        cfg.preset,
        "-movflags",
        "+faststart",
    ]

    if cfg.threads:
        cmd += ["-threads", str(cfg.threads)]

    cmd.append(str(cfg.output))

    print("Running command:")
    print(" ".join(shlex.quote(x) for x in cmd))

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"FFmpeg failed with exit code {exc.returncode}", file=sys.stderr)
        return exc.returncode
    return 0


def main() -> int:
    try:
        cfg = parse_args()
        return run(cfg)
    except FileNotFoundError as exc:
        print(
            f"Required binary missing: {exc}. Install FFmpeg (ffmpeg + ffprobe) and retry.",
            file=sys.stderr,
        )
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
