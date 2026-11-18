#!/usr/bin/env python3
import argparse
import multiprocessing
import os
import csv
import subprocess


def report(e):
    print(f'ERROR: {e}', flush=True)


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-input', type=str, default=os.path.join(os.path.curdir, 'tracks'), help='Input folder')
    parser.add_argument('-output', type=str, default=os.path.join(os.path.curdir, 'prepared_tracks'),
                        help='Output folder')
    parser.add_argument('-t', type=int, default=-14, help='Target volume in LUFS (-70 to -5)')
    parser.add_argument('-f', type=float, default=3, help='Fade duration (seconds)')
    parser.add_argument('-sprint', action='store_true', help='Tracks 74-89 become 30 s with 2 s fades')
    parser.add_argument('-j', type=int, default=4, help='Parallel ffmpeg jobs (default 4)')
    
    args = parser.parse_args()
    ss_index = 2

    from prepare_track import prepare_track
    
    if not os.path.exists(args.input):
        exit(f'Input folder not found: {args.input}')

    if not os.path.exists(args.output):
        os.mkdir(args.output)
    
    with multiprocessing.Pool(args.j) as p:
        with open('klub.csv', 'rt', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            
            for i, row in enumerate(reader, 1):
                
                infile = os.path.join(args.input, str(i) + '.wav')
                outfile = os.path.join(args.output, str(i) + '.wav')
                
                if not os.path.exists(infile):
                    continue
                if args.sprint:
                    if i >= 74 and i <= 89:
                        print(f"short track {i}")
                        p.apply_async(prepare_track, (infile, outfile, row[2], args.t, 2, '30'), error_callback=report)
                        continue
                    
                p.apply_async(prepare_track, (infile, outfile, row[2], args.t, args.f), error_callback=report)

        p.close()
        p.join()


