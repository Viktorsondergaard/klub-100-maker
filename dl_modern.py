import csv
import shutil
import yt_dlp
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

def download_track(task_data):
    """Download a single track using yt-dlp Python API with proper cleanup"""
    import signal
    import sys
    import os

    # Set up signal handler to ensure clean termination
    def signal_handler(signum, frame):
        print(f"Process {os.getpid()} received signal {signum}, terminating...")
        sys.exit(1)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    name, link, outfile, track_num, total = task_data
    
    print(f"[{track_num}/{total}] Starting: {name}")
    
    # Remove .wav extension since yt-dlp will add it
    outfile_base = outfile.rsplit('.wav', 1)[0] if outfile.endswith('.wav') else outfile

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outfile_base,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
        }],
        'extractor_args': {
            'youtube': {
                'player_client': ['default']
            }
        },
        'quiet': True,  # Suppress yt-dlp output
        'no_warnings': False,
        'socket_timeout': 30,  # Add timeout to prevent hanging
        'retries': 1,  # Limit retries
    }

    ydl = None
    try:
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        ydl.download([link])

        print(f"[{track_num}/{total}] ✓ SUCCESS: {name}")
        return {'success': True, 'name': name, 'track_num': track_num, 'error': None}

    except yt_dlp.DownloadError as e:
        print(f"[{track_num}/{total}] ✗ DOWNLOAD ERROR: {name}")
        print(f"  Error: {str(e)[:200]}...")
        return {'success': False, 'name': name, 'track_num': track_num, 'error': str(e)}
    except Exception as e:
        print(f"[{track_num}/{total}] ✗ ERROR: {name} - {e}")
        return {'success': False, 'name': name, 'track_num': track_num, 'error': str(e)}
    finally:
        # Explicit cleanup
        if ydl:
            try:
                # Clean up any open connections
                if hasattr(ydl, '_opener') and ydl._opener:
                    ydl._opener.close()
            except:
                pass

        # Force garbage collection
        import gc
        gc.collect()

        # Ensure process exits cleanly
        sys.stdout.flush()
        sys.stderr.flush()


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
                
            name = row[0]  # name_index = 0
            link = row[1]  # link_index = 1
            
            if not link or not link.strip():
                continue
                
            outfile = tracks_path / f"{i}.wav"
            tasks.append((name, link.strip(), str(outfile), i, 0))  # total will be updated
    
    # Update total count in all tasks
    total_tasks = len(tasks)
    tasks = [(name, link, outfile, track_num, total_tasks) for name, link, outfile, track_num, _ in tasks]
    
    print(f"🎵 Starting download of {total_tasks} tracks with parallel processing...")
    
    # Use ProcessPoolExecutor for parallel downloads
    successful = 0
    failed = 0
    
    # Use max_workers to control concurrency (adjust as needed)
    max_workers = min(15, total_tasks)  # Reduce workers to prevent resource exhaustion

    try:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(download_track, task): task for task in tasks}

            # Process completed tasks as they finish with timeout
            try:
                for future in as_completed(future_to_task, timeout=1800):  # 30 minute total timeout
                    try:
                        result = future.result(timeout=60)  # 1 minute per task timeout

                        if result['success']:
                            successful += 1
                        else:
                            failed += 1

                        # Progress update
                        completed = successful + failed
                        print(f"📊 Progress: {completed}/{total_tasks} ({successful} success, {failed} failed)")

                    except Exception as e:
                        failed += 1
                        print(f"❌ Task failed with exception: {e}")

            except Exception as e:
                print(f"⚠️ Processing interrupted: {e}")
                # Cancel remaining futures
                for future in future_to_task:
                    future.cancel()

    except KeyboardInterrupt:
        print("\n🛑 Download interrupted by user")
    except Exception as e:
        print(f"💥 Executor error: {e}")

    print(f"\n🎉 DOWNLOAD COMPLETE!")
    print(f"📈 Total tracks: {total_tasks}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📁 Files saved to: {tracks_path.absolute()}")


if __name__ == '__main__':
    main()
