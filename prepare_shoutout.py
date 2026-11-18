#!/usr/bin/env python3
import argparse
import os
import subprocess

from imageio_ffmpeg import get_ffmpeg_exe

# Static ffmpeg shipped in the imageio-ffmpeg wheel (override with IMAGEIO_FFMPEG_EXE).
FFMPEG = get_ffmpeg_exe()


def prepare_shoutout(input, output, t=-14):
    print('Preparing', input + '...')
    
    # two-pass ebu r128 loudnorm filter
    # loudnorm pass 1
    p1 = subprocess.Popen([FFMPEG, '-loglevel', 'error',
                           '-i', input,
                           '-pass', '1', '-af', 'loudnorm=I=' + str(t) + ':TP=-1',
                           '-f', 'wav', '-y', os.devnull],  # generate log in null
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE)
    
    # loudnorm pass 2
    p2 = subprocess.Popen([FFMPEG, '-loglevel', 'error',
                           '-i', input,
                           '-pass', '2', '-af', 'loudnorm=I=' + str(t) + ':TP=-1',
                           '-ar', '44100', '-ac', '2',  # loudnorm upsamples to 192 kHz
                           '-f', 'wav', '-y', output],
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE)
    
    p1.communicate()
    p2.communicate()

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=str, help='Input file')
    parser.add_argument('output', type=str, help='Output file')
    parser.add_argument('-t', type=int, default=-14, help='Target volume in LUFS (-70 to -5)')
    
    args = parser.parse_args()
    
    prepare_shoutout(args.input, args.output, args.t)
