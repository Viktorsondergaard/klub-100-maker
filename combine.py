#!/usr/bin/env python3
import argparse
import csv
import subprocess
import os

from imageio_ffmpeg import get_ffmpeg_exe

# Static ffmpeg shipped in the imageio-ffmpeg wheel (override with IMAGEIO_FFMPEG_EXE).
FFMPEG = get_ffmpeg_exe()

parser = argparse.ArgumentParser()
parser.add_argument('-beercounter', action='store_true',
                    help='Use shoutouts/0_stiv.wav as the filler before tracks 17, 34, 51, 67 and 83')
parser.add_argument('-shoutouts', type=str, default=os.path.join(os.path.curdir, 'prepared_shoutouts'),
                    help='Input shoutouts folder')
parser.add_argument('-tracks', type=str, default=os.path.join(os.path.curdir, 'prepared_tracks'),
                    help='Input tracks folder')
parser.add_argument('-output', type=str, default=os.path.join(os.path.curdir, 'klub100.mp3'),
                    help='Output file')

args = parser.parse_args()

if not os.path.exists(args.shoutouts) or not os.path.exists(args.tracks):
    exit(f'Missing input folder: {args.shoutouts} or {args.tracks}')

inputs = []

with open('klub.csv', 'rt', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    
    for i, row in enumerate(reader, 1):
        if os.path.exists(os.path.join(args.shoutouts, f"{i}.wav")):
            inputs.append('-i')
            inputs.append(os.path.join(args.shoutouts, str(i) + '.wav'))
        else:
            if not args.beercounter:
                inputs.append('-i')
                inputs.append(os.path.join(args.shoutouts, str(0) + '.wav'))
            else:
                inputs.append('-i')
                
                if i == 17 or i == 34 or i == 51 or i == 67 or i == 83:
                    inputs.append(os.path.join(args.shoutouts, "0_stiv" + '.wav'))
                else:
                    inputs.append(os.path.join(args.shoutouts, str(0) + '.wav'))

        inputs.append('-i')
        inputs.append(os.path.join(args.tracks, str(i) + '.wav'))

missing = [p for p in inputs[1::2] if not os.path.exists(p)]
if missing:
    exit('Missing input files:\n  ' + '\n  '.join(missing))

n = len(inputs) // 2
# Inputs mix mono/stereo, 44.1/48/192 kHz and mp3/aac/pcm; force one format per
# input before concat, otherwise ffmpeg may negotiate e.g. a mono output.
filter_ = ''.join(f'[{a}:a]aformat=sample_rates=44100:channel_layouts=stereo[a{a}];' for a in range(n)) \
    + ''.join(f'[a{a}]' for a in range(n)) + f'concat=n={n}:v=0:a=1[out]'

print(f'Combining {n} inputs ({n // 2} tracks) -> {args.output}', flush=True)
result = subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-stats',
                         *inputs, '-filter_complex', filter_, '-map', '[out]',
                         '-c:a', 'libmp3lame', '-q:a', '2', '-y', args.output])
exit(result.returncode)
