#!/usr/bin/python3
import argparse
import glob
import pathlib

import buffham.parse as bh

def main(dir: pathlib.Path):
    for bh_file in glob.glob(str(dir.absolute() / '**/*.bh'), recursive=True):
        bh_file = pathlib.Path(bh_file)
        messages = bh.Parser.parse_file(bh_file)
        bh.Generator.generate(bh_file, messages)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate BuffHam definitions')
    parser.add_argument('--dir', '-d', help='Directory to recursively generate through', default=str(pathlib.Path.cwd()))
    
    args = parser.parse_args()

    main(pathlib.Path(args.dir))
