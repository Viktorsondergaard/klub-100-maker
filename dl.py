#!/usr/bin/env python3

import csv
import multiprocessing
import shutil
import os
import subprocess


def download(name, link, outfile):
    print(f'Downloading {name}...', flush=True)

    try:
        result = subprocess.run(['yt-dlp',
                                '--no-playlist',
                                '--js-runtimes', 'node',
                                '--remote-components', 'ejs:github',
                                '--extract-audio',
                                '--audio-format', 'wav',
                                '-o', outfile, link],
                               capture_output=True,
                               text=True,
                               timeout=120)

        if result.returncode != 0:
            print(f'FAILED {name}: {result.stderr.strip()[-200:]}', flush=True)
            return False
        else:
            print(f'OK {name}', flush=True)
            return True

    except subprocess.TimeoutExpired:
        print(f'TIMEOUT {name}', flush=True)
        return False
    except Exception as e:
        print(f'ERROR {name}: {e}', flush=True)
        return False


if __name__ == '__main__':
    # Clear yt-dlp cache once before starting
    subprocess.run(['yt-dlp', '--rm-cache-dir'], capture_output=True)

    tracks_path = os.path.join(os.path.curdir, 'tracks')

    if os.path.exists(tracks_path):
        shutil.rmtree(tracks_path)
    os.mkdir(tracks_path)

    tasks = []
    with open('klub.csv', 'rt') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for i, row in enumerate(reader, 1):
            if len(row) < 2:
                continue
            name = row[0]
            link = row[1]
            if not link.strip():
                continue
            outfile = os.path.join(tracks_path, str(i) + '.wav')
            tasks.append((name, link, outfile))

    print(f"Downloading {len(tasks)} tracks...", flush=True)

    with multiprocessing.Pool() as pool:
        results = pool.starmap(download, tasks)

    successful = sum(results)
    print(f"\n=== DONE: {successful}/{len(tasks)} successful ===")
