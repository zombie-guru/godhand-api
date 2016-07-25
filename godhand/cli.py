import argparse
import json
import logging
import sys

from .opendata import iterate_manga


def main():
    ap = argparse.ArgumentParser('godhand-cli')
    ap.add_argument('--log-level', default='DEBUG')
    s = ap.add_subparsers(dest='cmd')

    s.add_parser('dbpedia-dump')

    args = ap.parse_args()
    logging.basicConfig(
        level=args.log_level,
        format='%(asctime)s[%(name)s][%(levelname)s]: %(message)s',
    )
    if args.cmd == 'dbpedia-dump':
        dbpedia_dump()


def dbpedia_dump():
    for manga in iterate_manga():
        json.dump(manga, sys.stdout)
        sys.stdout.write('\n')
