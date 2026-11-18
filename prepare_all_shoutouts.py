#!/usr/bin/env python3
import argparse
import multiprocessing
import os


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-input', type=str, default=os.path.join(os.path.curdir, 'shoutouts'), help='Input folder')
    parser.add_argument('-output', type=str, default=os.path.join(os.path.curdir, 'prepared_shoutouts'),
                        help='Output folder')
    parser.add_argument('-t', type=int, default=-14, help='Target volume in LUFS (-70 to -5)')
    parser.add_argument('-j', type=int, default=4, help='Parallel ffmpeg jobs (default 4)')
    
    args = parser.parse_args()
    
    from prepare_shoutout import prepare_shoutout
    
    if not os.path.exists(args.input):
        exit(f'Input folder not found: {args.input}')
    
    if not os.path.exists(args.output):
        os.mkdir(args.output)
    
    with multiprocessing.Pool(args.j) as p:
        # Every .wav in the folder: numbered ones (1.wav = before song 1) plus
        # fillers like 0.wav / 0_stiv.wav that combine.py falls back to.
        for name in sorted(os.listdir(args.input)):
            if not name.lower().endswith('.wav'):
                continue
            infile = os.path.join(args.input, name)
            outfile = os.path.join(args.output, name)
            p.apply_async(prepare_shoutout, (infile, outfile, args.t),
                          error_callback=lambda e: print(f'ERROR: {e}', flush=True))
        
        p.close()
        p.join()
