# klub-100-maker

Toolkit for building a Klub 100 playlist from a CSV tracklist.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [ffmpeg](https://ffmpeg.org/) installed and on PATH
- [Node.js](https://nodejs.org/) installed and on PATH (required by yt-dlp for YouTube signature decryption)

## Getting Started

```bash
# Install dependencies (handled automatically by uv on first run)
uv sync

# Or run scripts directly — uv installs deps on the fly
uv run python dl.py
```

> **Tip:** If downloads are failing, yt-dlp may be outdated. Run `uv lock --upgrade-package yt-dlp && uv sync` to pull the latest version.

## Mappestruktur

Inden du begynder, bor mappen se saadan ud:

```
klub-100-maker/
├── shoutouts/
│   ├── 1.wav
│   ├── 2.wav
│   └── ...
├── klub.csv
├── dl.py
├── prepare_shoutout.py
├── prepare_track.py
├── prepare_all_shoutouts.py
├── prepare_all_tracks.py
└── combine.py
```

`shoutouts/n.wav` indeholder skud ud'et til den n'te sang i klub 100'en. Skud ud'et kommer *for* sangen, saa `shoutouts/1.wav` er jeres intro-skud-ud.

## klub.csv

CSV-fil med information om sangene. Hver raekke er en sang:

| Kolonne | Indhold |
|---------|---------|
| 1 | Sangens navn |
| 2 | YouTube/SoundCloud link |
| 3 | Timestamp (sekunder) hvor jeres minut af sangen starter |

## Byg en Klub 100

```bash
# 1. Download alle sange til ./tracks/
uv run python dl.py

# 2. Trim, fade og loudness-normaliser sange -> ./prepared_tracks/
uv run python prepare_all_tracks.py

# 3. Loudness-normaliser skud ud -> ./prepared_shoutouts/
uv run python prepare_all_shoutouts.py

# 4. Kombiner til endelig klub100.mp3
uv run python combine.py
```

## Nyttige kommandoer

```bash
ls tracks/ | wc -l          # Antal downloadede filer
for f in *.m4a; do mv -- "$f" "${f%.m4a}.wav"; done  # Konverter m4a -> wav
```
