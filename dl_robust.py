#!/usr/bin/env python3

import csv
import shutil
import subprocess
import signal
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed, TimeoutError
from pathlib import Path


def download_track_subprocess(task_data):
    """Download a single track using subprocess yt-dlp for better process isolation"""
    name, link, outfile, track_num, total = task_data
    
    print(f"[{track_num}/{total}] Starting: {name}")
    
    # Set up process group to ensure we can kill child processes
    def preexec_fn():
        os.setsid()
    
    try:
        # Use subprocess with proper timeout and cleanup
        result = subprocess.run([
            'uv', 'run', 'yt-dlp',
            '--rm-cache-dir',
            '--extract-audio',
            '--audio-format', 'wav',
            '--extractor-args', 'youtube:player_client=default',
            '--socket-timeout', '30',
            '--retries', '1',
            '--no-continue',  # Don't resume partial downloads
            '-o', outfile.replace('.wav', ''),  # Remove .wav as yt-dlp adds it
            link
        ], 
        capture_output=True, 
        text=True, 
        timeout=120,  # 2 minute timeout per download
        cwd='/home/vso/Documents/Klub100ere/klub-100-maker',
        preexec_fn=preexec_fn)

        if result.returncode == 0:
            print(f"[{track_num}/{total}] ✅ SUCCESS: {name}")
            return {'success': True, 'name': name, 'track_num': track_num, 'error': None}
        else:
            print(f"[{track_num}/{total}] ❌ FAILED: {name}")
            error_msg = result.stderr[:200] if result.stderr else f"Return code: {result.returncode}"
            print(f"  Error: {error_msg}...")
            return {'success': False, 'name': name, 'track_num': track_num, 'error': error_msg}

    except subprocess.TimeoutExpired as e:
        print(f"[{track_num}/{total}] ⏰ TIMEOUT: {name}")
        # Kill the process group to ensure cleanup
        try:
            os.killpg(e.process.pid, signal.SIGTERM)
        except:
            pass
        return {'success': False, 'name': name, 'track_num': track_num, 'error': 'Timeout'}
    except Exception as e:
        print(f"[{track_num}/{total}] 💥 ERROR: {name} - {e}")
        return {'success': False, 'name': name, 'track_num': track_num, 'error': str(e)}


def main():
    tracks_path = Path('./tracks')
    
    # Clean and create tracks directory
    if tracks_path.exists():
        shutil.rmtree(tracks_path)
    tracks_path.mkdir()
    
    # Collect all tasks from CSV
    tasks = []
    with open('klub.csv', 'rt') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        
        for i, row in enumerate(reader, 1):
            if len(row) < 2:
                continue
                
            name = row[0]
            link = row[1]
            
            if not link or not link.strip():
                continue
                
            outfile = str(tracks_path / f"{i}.wav")
            tasks.append((name, link.strip(), outfile, i, 0))
    
    # Update total count in all tasks
    total_tasks = len(tasks)
    tasks = [(name, link, outfile, track_num, total_tasks) for name, link, outfile, track_num, _ in tasks]
    
    print(f"🚀 Starting subprocess download of {total_tasks} tracks...")
    
    # Use ProcessPoolExecutor for parallel downloads
    successful = 0
    failed = 0
    
    # Reduce workers to prevent resource exhaustion
    max_workers = min(10, total_tasks)
    
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, shutting down...")
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(download_track_subprocess, task): task for task in tasks}
            
            # Process completed tasks as they finish
            try:
                for future in as_completed(future_to_task, timeout=3600):  # 1 hour total timeout
                    try:
                        result = future.result(timeout=150)  # 2.5 minute per task timeout
                        
                        if result['success']:
                            successful += 1
                        else:
                            failed += 1
                        
                        # Progress update
                        completed = successful + failed
                        progress = (completed / total_tasks) * 100
                        print(f"📊 Progress: {completed}/{total_tasks} ({progress:.1f}%) - ✅ {successful} success, ❌ {failed} failed")
                        
                    except TimeoutError:
                        failed += 1
                        print(f"❌ Task timed out")
                    except Exception as e:
                        failed += 1
                        print(f"❌ Task failed with exception: {e}")
                        
            except TimeoutError:
                print("⚠️ Overall timeout reached, cancelling remaining tasks...")
                for future in future_to_task:
                    future.cancel()
                    
    except KeyboardInterrupt:
        print("\n🛑 Download interrupted by user")
    except Exception as e:
        print(f"💥 Executor error: {e}")
    finally:
        print(f"\n🎉 DOWNLOAD COMPLETE!")
        print(f"📈 Total tracks: {total_tasks}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📁 Files saved to: {tracks_path.absolute()}")


if __name__ == '__main__':
    main()
