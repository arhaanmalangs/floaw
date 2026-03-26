# FLOAW

FLOAW is a **watermark-free video editing software** built as a powerful command-line application on top of FFmpeg.

It supports the majority of practical editing workflows for creators and teams while keeping exports clean (no branding or forced watermark).

## Features

- ✂️ Trim with start/end/duration
- 🧩 Concatenate multiple video clips
- 📐 Resize and crop
- 🔄 Rotate and flip
- ⚡ Speed up / slow down (video + audio)
- 🎨 Color tools (brightness, contrast, saturation, grayscale)
- 🧼 Blur and sharpen
- 📝 Add text overlays (position, color, size, custom font)
- 🖼️ Add image overlays (logos/stickers)
- 🌅 Fade in / fade out for video and audio
- 🔊 Audio controls: mute, volume, replace audio, mix background track
- 🎞️ FPS control
- 🧰 Codec/quality tuning (CRF/preset, codecs, threads)
- 🚫 **No watermark added by FLOAW**

## Requirements

- Python 3.10+
- FFmpeg and FFprobe available in PATH

## Quick start

```bash
python3 floaw.py input.mp4 -o output.mp4 --overwrite
```

## Example commands

### 1) Trim and resize

```bash
python3 floaw.py input.mp4 -o trimmed.mp4 --start 5 --duration 12 --width 1280 --height 720 --overwrite
```

### 2) Speed up + fade + text

```bash
python3 floaw.py input.mp4 -o social.mp4 \
  --speed 1.35 --fade-in 0.5 --fade-out 0.5 \
  --text "New Drop" --text-color yellow --text-size 56 \
  --overwrite
```

### 3) Overlay image and replace audio

```bash
python3 floaw.py input.mp4 -o final.mp4 \
  --image-overlay badge.png --image-scale 180:-1 --image-x 24 --image-y 24 \
  --audio-file soundtrack.mp3 --replace-audio --audio-volume 0.9 \
  --overwrite
```

### 4) Merge multiple clips

```bash
python3 floaw.py clip1.mp4 clip2.mp4 clip3.mp4 -o merged.mp4 --overwrite
```

## Help

```bash
python3 floaw.py --help
```


## Deploy note (Vercel)

This project is a **CLI tool**, not a server-rendered web application. A basic landing page is included at `public/index.html` with `vercel.json` rewrites so Vercel deployments do not return a 404.

