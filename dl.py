
#!/usr/bin/env python3

import argparse
import csv
import multiprocessing
import shutil
import os

# Dependencies are installed via: uv pip install -r requirements.txt


def download(name, link, outfile):
    import subprocess
    import sys

    print('Downloading', name, 'from', link + '...')

    try:
        # Use subprocess.run with proper working directory
        result = subprocess.run(['uv', 'run', 'yt-dlp',
                                '--rm-cache-dir',
                                '--extract-audio',
                                '--audio-format', 'wav',
                                '--extractor-args', 'youtube:player_client=default',
                                '-o', outfile, link],
                               capture_output=True,
                               text=True,
                               timeout=300,  # 5 minute timeout
                               cwd='/home/vso/Documents/Klub100ere/klub-100-maker')

        if result.returncode != 0:
            print(f'Error downloading {name} from {link}', file=sys.stderr)
            print(f'Stderr: {result.stderr}', file=sys.stderr)
            return False
        else:
            return True

    except subprocess.TimeoutExpired:
        print(f'Timeout downloading {name} from {link}', file=sys.stderr)
        return False
    except FileNotFoundError as e:
        print(f'Command not found: {e}', file=sys.stderr)
        return False
    except Exception as e:
        print(f'Exception downloading {name}: {e}', file=sys.stderr)
        return False


if __name__ == '__main__':
    
    tracks_path = os.path.join(os.path.curdir, 'tracks')
    name_index = 0
    link_index = 1
    
    if os.path.exists(tracks_path):
        shutil.rmtree(tracks_path)
    
    os.mkdir(tracks_path)
    
    # Use multiprocessing for parallel downloads with proper task tracking
    with multiprocessing.Pool() as pool:
        async_results = []

        with open('klub.csv', 'rt') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')

            for i, row in enumerate(reader, 1):
                if len(row) < 2:
                    continue

                name = row[name_index]
                link = row[link_index]

                if link == "" or not link.strip():
                    continue

                outfile = os.path.join(tracks_path, str(i) + '.wav')

                # Submit task and collect AsyncResult
                async_result = pool.apply_async(download, (name, link, outfile))
                async_results.append((async_result, name, i))

        # Close pool to prevent new tasks
        pool.close()

        print(f"Submitted {len(async_results)} download tasks")

        # Wait for each task to complete
        successful = 0
        for j, (async_result, name, track_num) in enumerate(async_results, 1):
            try:
                success = async_result.get(timeout=600)  # 10 min timeout per task
                if success:
                    successful += 1
                    print(f"[{j}/{len(async_results)}] ✓ Track {track_num}: {name}")
                else:
                    print(f"[{j}/{len(async_results)}] ✗ Track {track_num}: {name}")
            except Exception as e:
                print(f"[{j}/{len(async_results)}] ✗ Track {track_num} ERROR: {name} - {e}")

        # Wait for all workers to finish
        pool.join()

    print(f"\n=== DOWNLOAD COMPLETE ===")
    print(f"Total tracks: {len(async_results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(async_results) - successful}")
