#!/usr/bin/env python3
"""Download every track in klub.csv to ./tracks/<row>.wav.

Dropbox share links are fetched directly (``?dl=1``) and converted with ffmpeg;
everything else (YouTube, SoundCloud, ...) goes through yt-dlp.
"""

import argparse
import csv
import multiprocessing
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request

from imageio_ffmpeg import get_ffmpeg_exe

# Static ffmpeg shipped in the imageio-ffmpeg wheel (override with IMAGEIO_FFMPEG_EXE).
FFMPEG = get_ffmpeg_exe()

# Run yt-dlp from the same venv as this script, and make sure the venv's bin
# dir (which holds the bundled `deno` binary) is on PATH for the JS solver.
VENV_BIN = os.path.dirname(sys.executable)
ENV = {**os.environ, 'PATH': VENV_BIN + os.pathsep + os.environ.get('PATH', '')}
YT_DLP = [sys.executable, '-m', 'yt_dlp']


DROPBOX_HOSTS = ('dropbox.com', 'www.dropbox.com', 'dl.dropbox.com', 'dl.dropboxusercontent.com')


def is_dropbox(link):
    return urllib.parse.urlsplit(link).hostname in DROPBOX_HOSTS


def dropbox_direct_url(link):
    """Turn a Dropbox share link into a direct-download link.

    Keeps every query param (the ``rlkey`` is required for /scl/ links) and
    forces ``dl=1`` so Dropbox returns the file instead of the preview page.
    """
    parts = urllib.parse.urlsplit(link)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k not in ('dl', 'raw')]
    query.append(('dl', '1'))
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def download_dropbox(link, tmp_base, tmp_wav, timeout):
    """Fetch a Dropbox file and convert it to tmp_wav. Returns an error string or None."""
    tmp_src = tmp_base + '.src'
    try:
        request = urllib.request.Request(dropbox_direct_url(link), headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=timeout) as response, open(tmp_src, 'wb') as f:
            content_type = response.headers.get('Content-Type', '')
            shutil.copyfileobj(response, f)

        with open(tmp_src, 'rb') as f:
            head = f.read(4)
        if head.startswith(b'PK'):
            return 'link points to a Dropbox folder (got a zip) - use the link to the single file'
        if 'text/html' in content_type:
            return 'got a web page instead of a file - is the link password-protected or not shared?'

        result = subprocess.run([FFMPEG, '-loglevel', 'error', '-i', tmp_src, '-vn', '-y', tmp_wav],
                                capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return 'ffmpeg could not read the file: ' + result.stderr.strip()[-200:]
        return None
    finally:
        if os.path.exists(tmp_src):
            os.remove(tmp_src)


def download(name, link, outfile, timeout):
    print(f'Downloading {name}...', flush=True)

    # Download next to the target under a temp name and only replace the real
    # file on success, so a failed download never destroys a working track.
    base, _ = os.path.splitext(outfile)
    tmp_base = base + '.part-dl'
    tmp_wav = tmp_base + '.wav'
    if os.path.exists(tmp_wav):
        os.remove(tmp_wav)

    try:
        if is_dropbox(link):
            error = download_dropbox(link, tmp_base, tmp_wav, timeout)
            if error or not os.path.exists(tmp_wav):
                print(f'FAILED {name}: {error}', flush=True)
                return False
            os.replace(tmp_wav, outfile)
            print(f'OK {name}', flush=True)
            return True

        result = subprocess.run([*YT_DLP,
                                 '--no-playlist',
                                 '--ffmpeg-location', FFMPEG,
                                 '--extract-audio',
                                 '--audio-format', 'wav',
                                 '-o', tmp_base + '.%(ext)s', link],
                                capture_output=True,
                                text=True,
                                env=ENV,
                                timeout=timeout)

        if result.returncode != 0 or not os.path.exists(tmp_wav):
            print(f'FAILED {name}: {result.stderr.strip()[-200:]}', flush=True)
            return False
        os.replace(tmp_wav, outfile)
        print(f'OK {name}', flush=True)
        return True

    except subprocess.TimeoutExpired:
        print(f'TIMEOUT {name}', flush=True)
        return False
    except Exception as e:
        print(f'ERROR {name}: {e}', flush=True)
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-j', type=int, default=8, help='Parallel downloads (default 8)')
    parser.add_argument('-timeout', type=int, default=300, help='Per-track timeout in seconds (default 300)')
    parser.add_argument('-skip-existing', action='store_true',
                        help='Skip rows whose tracks/<n>.wav already exists instead of re-downloading')
    args = parser.parse_args()

    # Clear yt-dlp cache once before starting
    subprocess.run([*YT_DLP, '--rm-cache-dir'], capture_output=True, env=ENV)

    tracks_path = os.path.join(os.path.curdir, 'tracks')

    # Never wipe the folder: rows without a URL (Dropbox tracks) are copied in by hand.
    os.makedirs(tracks_path, exist_ok=True)

    tasks = []
    with open('klub.csv', 'rt', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for i, row in enumerate(reader, 1):
            if len(row) < 2:
                continue
            name = row[0]
            link = row[1].strip()
            # Rows without a URL (e.g. the placeholder "Dropboxen") are placed in tracks/ by hand.
            if not link.startswith(('http://', 'https://')):
                continue
            outfile = os.path.join(tracks_path, str(i) + '.wav')
            if args.skip_existing and os.path.exists(outfile):
                continue
            tasks.append((name, link, outfile, args.timeout))

    print(f"Downloading {len(tasks)} tracks...", flush=True)

    with multiprocessing.Pool(args.j) as pool:
        results = pool.starmap(download, tasks)

    successful = sum(results)
    failed_tracks = [tasks[i][0] for i, ok in enumerate(results) if not ok]

    print(f"\n=== DONE: {successful}/{len(tasks)} successful ===")
    if failed_tracks:
        print("\nFailed tracks:")
        for name in failed_tracks:
            print(f"  - {name}")
