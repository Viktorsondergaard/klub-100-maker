# CLAUDE.md

Guide for Claude Code agents (and humans) working in this repo. Read it fully before touching anything.

## What this is

A small Python CLI toolkit that builds a **Klub 100**: a drinking-game mix of ~100 one-minute song clips, each preceded by a short spoken "skud ud" (shoutout), concatenated into one `klub100.mp3`. Danish student-association tooling, so song names, CSV notes and parts of the README are Danish.

Everything is driven by `klub.csv`. There is no package, no tests, no CI. Just six scripts run in order from the repo root.

```
klub.csv ──► dl.py ──► tracks/<n>.wav ──► prepare_all_tracks.py ──► prepared_tracks/<n>.wav ──┐
                         ▲ (Dropbox rows copied in by hand)                                        ├─► combine.py ──► klub100.mp3
shoutouts/*.wav ─────────────────────────► prepare_all_shoutouts.py ──► prepared_shoutouts/*.wav ─┘
```

## Setup: uv is the only prerequisite

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # once
uv sync                                           # creates .venv with everything
```

No system Python, Node.js or ffmpeg is needed. Dependencies (`pyproject.toml`, locked in `uv.lock`):

| Need | Provided by | Notes |
|---|---|---|
| Python ≥3.12 | uv | uv downloads it if missing |
| yt-dlp | `yt-dlp[default,deno]` | `default` extra → `yt-dlp-ejs` (YouTube JS-challenge solver scripts) + brotli/certifi/mutagen/etc. |
| JS runtime for YouTube | `deno` PyPI package (via `[deno]` extra) | Binary lands in `.venv/bin/deno`. yt-dlp ≥2025.11 needs a JS runtime for YouTube; **don't add `--js-runtimes node` or `--remote-components`, they are obsolete here** |
| ffmpeg | `imageio-ffmpeg` | Static ffmpeg (9.x) inside the wheel. Every script uses `FFMPEG = get_ffmpeg_exe()`, **never a bare `ffmpeg`**. Override with env `IMAGEIO_FFMPEG_EXE=/path/to/ffmpeg`. No `ffprobe` is shipped; yt-dlp falls back to ffmpeg for probing |

`ffprobe` from the system (if installed) is handy for inspection but no script depends on it.

### When YouTube downloads break

Almost always yt-dlp is stale:

```bash
uv lock --upgrade-package yt-dlp --upgrade-package yt-dlp-ejs --upgrade-package deno && uv sync
uv run yt-dlp -v --simulate --no-playlist -f bestaudio '<youtube-url>'   # cheap check, downloads nothing
```

A healthy `-v` run shows `JS runtimes: deno-…` and `[jsc:deno] Solving JS challenges using deno`. Bump the `>=` floor in `pyproject.toml` when upgrading.

## Data conventions (critical)

- **CSV row number (1-based) = file name everywhere.** Row 7 → `tracks/7.wav` → `prepared_tracks/7.wav`, shoutout `7.wav` plays *before* song 7. Rows are counted even when skipped, so **never reorder, insert or delete rows without renaming the matching audio files.**
- `klub.csv`: UTF-8, **no header**, may have CRLF endings and no trailing newline. Count rows with Python's `csv` module, not `wc -l` (the current file has 102 rows but `wc -l` says 101).
  - col 1: song name (display/logging only)
  - col 2: link. Only values starting with `http(s)://` (YouTube, SoundCloud…) are downloaded. Anything else (`Dropboxen`, `dropbox`, empty) means the WAV is copied into `tracks/<n>.wav` by hand.
  - col 3: start offset in seconds for the 60 s clip (`prepare_all_tracks.py` reads `row[2]`, so it must exist and be numeric)
  - col 4+: free-form notes, ignored
- `klub_temp.csv` and other CSV variants are the user's scratch copies. **Don't edit or commit CSVs unless asked.**
- Shoutouts (`shoutouts/`) are raw recordings named `<n>.wav` plus fillers: `0.wav` (default filler for rows without their own), `0_stiv.wav` (used with `-beercounter`), `0_long.wav` (spare). Files are often really mp3/aac with a `.wav` extension; ffmpeg reads by content, so that's fine.
- `temp_songs/` is the user's own stash of already-cut 60 s clips (not used by any script).
- All audio (`tracks/`, `prepared_*`, `shoutouts/`, `temp_songs/`, `*.wav`, `*.mp3`, `*.m4a`) is git-ignored. **Never commit audio.**

## Scripts

All flags are single-dash argparse long names (`-j`, `-sprint`). Boolean flags are `store_true` switches: `-sprint`, never `-sprint True`. Run from repo root: `uv run <script>.py [flags]`.

| Script | Does | Flags (defaults) |
|---|---|---|
| `dl.py` | yt-dlp each URL row → `tracks/<n>.wav`. Downloads to `<n>.part-dl.wav` and `os.replace`s on success, so a failed download never destroys an existing track. Never wipes `tracks/`. Prints a failed-track list at the end | `-j 8`, `-timeout 300`, `-skip-existing` |
| `prepare_track.py` | One file: seek to `-ss`, trim to 60 s, loudnorm to `-t` LUFS (TP −1), fade in/out `-f` s, write 44.1 kHz stereo PCM WAV | `input output -ss 0 -t -14 -f 3` |
| `prepare_all_tracks.py` | `prepare_track` over every `tracks/<n>.wav` that exists, using CSV col 3 as start. `-sprint`: rows 74–89 become 30 s with 2 s fades | `-input tracks -output prepared_tracks -t -14 -f 3 -j 4 -sprint` |
| `prepare_shoutout.py` | One file: loudnorm only, 44.1 kHz stereo WAV | `input output -t -14` |
| `prepare_all_shoutouts.py` | `prepare_shoutout` over **every `*.wav` in `shoutouts/`** (numbered + fillers) | `-input shoutouts -output prepared_shoutouts -t -14 -j 4` |
| `combine.py` | For each CSV row i: shoutout `i.wav` (else `0.wav`; with `-beercounter`, `0_stiv.wav` before rows 17/34/51/67/83), then `prepared_tracks/i.wav`. Each input is `aformat`ted to 44.1 kHz stereo, then concat-filtered → libmp3lame VBR `-q:a 2` (~180 kbps). Fails early listing missing files. Overwrites output (`-y`) | `-shoutouts prepared_shoutouts -tracks prepared_tracks -output klub100.mp3 -beercounter` |

Full build:

```bash
uv run dl.py -skip-existing        # or without the flag to refresh every URL track
uv run prepare_all_tracks.py
uv run prepare_all_shoutouts.py
uv run combine.py -beercounter     # or without -beercounter
```

## Running heavy things: ask, cap, back up

The machine is a 22-core / 30 GB Linux box that has crashed from uncapped parallel ffmpeg before.

- **Don't run `dl.py`, `prepare_all_*`, `combine.py` or full-length ffmpeg transcodes unless the user explicitly asks for that run.** By default hand the user the exact command.
- When asked to run them, cap memory and parallelism:
  `systemd-run --user --scope --quiet -p MemoryMax=8G -p MemorySwapMax=0 -- uv run <script>.py -j 4`
- **Back up first:** `prepare_*` and `combine.py` overwrite outputs in place. Copy what will be overwritten (e.g. `klub100.mp3`, affected `prepared_tracks/<n>.wav`) to a sibling folder like `../klub100-backup-YYYY-MM-DD/`.
- Always safe: `-h`, `python -m py_compile`, `uv lock --check`, `ffprobe`, `ls`, reading CSVs, `yt-dlp --simulate` on one URL, tiny synthetic tests (`ffmpeg -f lavfi -i sine=f=440:d=4 …`) in a temp dir.

Reference timings on this machine (17 URL tracks, 102 rows, `-j 4`): dl ≈ 30 s, prepare tracks ≈ 30 s, shoutouts ≈ 1 s, combine ≈ 90 s (≈ 1 h 45 min of audio, ~135 MB mp3).

## Verifying a build

```bash
F=$(uv run python -c 'import imageio_ffmpeg as m; print(m.get_ffmpeg_exe())')
ffprobe -v error -show_entries stream=sample_rate,channels:format=duration -of default=nw=1 klub100.mp3   # expect 44100 / 2 channels
$F -hide_banner -nostats -i prepared_tracks/1.wav -af ebur128 -f null - 2>&1 | grep ' I:' | tail -1      # loudness ≈ -14 LUFS
$F -hide_banner -i klub100.mp3 -f null - 2>&1 | tr '\r' '\n' | grep -o 'time=[0-9:.]*' | tail -1         # true decoded length
```

The decoded length should equal Σ(prepared track durations for rows 1..N) + Σ(chosen shoutout durations). Some hand-placed songs are legitimately shorter than 60 s (e.g. rows 27, 63, 69).

## Known quirks (ask before "fixing")

- **Loudnorm is effectively single-pass.** The `-pass 1/2` args are no-ops for PCM and pass 1's measurements aren't fed into pass 2. Results land within ~±1.5 LUFS of target for tracks (fades lower the integrated value), exact for short shoutouts. A true two-pass (`print_format=json` → `measured_I/TP/LRA/thresh` + `linear=true`) would change the sound of the mix, so it's the user's call.
- Beercounter rows (17/34/51/67/83) and sprint rows (74–89) are hardcoded for a ~100-song klub.
- `prepare_track.py` pipes audio through 4 ffmpeg processes in memory (~50 MB per job), so keep `-j` modest.
- Old prepared tracks made before 2026-11-18 are 192 kHz (loudnorm upsamples; now resampled to 44.1 kHz). `combine.py` handles mixed formats, so re-preparing them is optional.
- `0.wav` in the repo root is a stray copy of the filler shoutout (ignored).

## Git

- Commit code/docs only; never audio or the user's CSV edits unless asked.
- `CLAUDE.md` is matched by the user's global gitignore, so add changes with `git add -f CLAUDE.md`.
