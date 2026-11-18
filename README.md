# klub-100-maker

Toolkit for building a Klub 100 (100 one-minute songs with shoutouts in between) from a CSV tracklist.

## Prerequisites

Only **[uv](https://docs.astral.sh/uv/)**. Everything else installs into the project's `.venv`:

| Tool | Comes from |
|------|------------|
| Python 3.12+ | uv downloads it if missing |
| yt-dlp | `yt-dlp[default,deno]` |
| YouTube JS challenge solver | `yt-dlp-ejs` (via the `default` extra) |
| JS runtime (Deno) | `deno` PyPI package (via the `deno` extra), so no Node.js is needed |
| ffmpeg | `imageio-ffmpeg` (static binary in the wheel), so there's no system ffmpeg |

```bash
# Install uv (once): https://docs.astral.sh/uv/getting-started/installation/
curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync
```

> **Downloads failing?** YouTube changes often. Update yt-dlp and its solver:
> `uv lock --upgrade-package yt-dlp --upgrade-package yt-dlp-ejs && uv sync`

To use a different ffmpeg binary, set `IMAGEIO_FFMPEG_EXE=/path/to/ffmpeg`.

## Mappestruktur

Inden du begynder, bør mappen se sådan ud:

```
klub-100-maker/
├── shoutouts/
│   ├── 0.wav        # standard-skud-ud, bruges hvor der ikke er et nummereret
│   ├── 0_stiv.wav   # kun med -beercounter
│   ├── 1.wav
│   └── ...
├── tracks/          # dl.py fylder den; Dropbox-sange lægges i manuelt som <række>.wav
├── klub.csv
└── *.py
```

`shoutouts/n.wav` er skud ud'et til den n'te sang. Det kommer *før* sangen, så `shoutouts/1.wav` er jeres intro. Filerne må gerne være mp3/m4a omdøbt til `.wav`; ffmpeg læser indholdet.

## klub.csv

UTF-8 CSV uden header. Række *n* = sang *n*. Byt ikke om på rækker uden også at omdøbe lydfilerne:

| Kolonne | Indhold |
|---------|---------|
| 1 | Sangens navn |
| 2 | YouTube/SoundCloud-link. Alt der ikke starter med `http` (fx `Dropboxen`) springes over af `dl.py` og skal lægges i `tracks/<n>.wav` manuelt |
| 3 | Timestamp (sekunder) hvor jeres minut af sangen starter |
| 4+ | Fri noter, ignoreres |

## Byg en Klub 100

```bash
# 1. Download alle link-sange til ./tracks/<n>.wav (overskriver kun de filer den downloader)
uv run dl.py                    # -j 8 parallelle, -skip-existing, -timeout 300

# 2. Trim til 60 s, loudness-normaliser (-14 LUFS) og fade -> ./prepared_tracks/
uv run prepare_all_tracks.py    # -j 4, -t -14, -f 3, -sprint

# 3. Loudness-normaliser alle skud ud (inkl. 0.wav, 0_stiv.wav) -> ./prepared_shoutouts/
uv run prepare_all_shoutouts.py # -j 4, -t -14

# 4. Kombiner til klub100.mp3 (stereo, ~180 kbps, overskriver eksisterende fil)
uv run combine.py               # -beercounter: 0_stiv.wav før sang 17/34/51/67/83
```

Step 2–4 bruger CPU og RAM. Hold `-j` lavt på en svag maskine.

## Nyttige kommandoer

```bash
ls tracks/ | wc -l                                     # Antal downloadede filer
for f in *.m4a; do mv -- "$f" "${f%.m4a}.wav"; done   # Omdøb m4a -> wav (ffmpeg læser indholdet uanset endelse)
```
