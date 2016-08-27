from itertools import islice
import argparse
import json
import logging
import sys

import couchdb.client
import couchdb.http

from .opendata import iterate_manga
from .opendata import replace_uri_prefixes
from .config import GodhandConfiguration
from .models import Series
from .utils import wait_for_couchdb


LOG = logging.getLogger(__file__)


def main():
    ap = argparse.ArgumentParser('godhand-cli')
    ap.add_argument('--log-level', default='DEBUG')
    s = ap.add_subparsers(dest='cmd')

    s.add_parser('dbpedia-dump')

    p = s.add_parser('upload')
    p.add_argument('--couchdb-url', default=None)

    args = ap.parse_args()
    logging.basicConfig(
        level=args.log_level,
        format='%(asctime)s[%(name)s][%(levelname)s]: %(message)s',
    )
    if args.cmd == 'dbpedia-dump':
        dbpedia_dump()
    elif args.cmd == 'upload':
        upload(args.couchdb_url)


def dbpedia_dump():
    for manga in iterate_manga():
        json.dump(manga, sys.stdout)
        sys.stdout.write('\n')


def upload(couchdb_url=None, lines=None):
    if lines is None:
        lines = sys.stdin
    cfg = GodhandConfiguration.from_env(couchdb_url=couchdb_url)
    db = get_db(cfg)
    docs = iterdocs(lines)
    while True:
        batch = list(islice(docs, 0, 500))
        if len(batch) == 0:
            break
        db.update(batch)
    Series.by_attribute.sync(db)
    Series.by_series_id.sync(db)


def iterdocs(lines):
    for n_line, line in enumerate(lines):
        if n_line and (n_line % 100) == 0:
            LOG.info('uploaded {} documents'.format(n_line))
        try:
            doc = json.loads(line)
        except ValueError:
            return
        keys = (
            'name', 'description', 'author', 'magazine', 'number_of_volumes')
        for key in keys:
            values = doc.pop(key)
            if values:
                doc[key] = values[0]
        try:
            doc['number_of_volumes'] = int(doc['number_of_volumes'])
        except KeyError:
            pass
        try:
            doc['genres'] = doc.pop('genre')
        except KeyError:
            pass
        doc['volumes'] = []

        doc_id = replace_uri_prefixes(doc.pop('uri')[0])
        yield Series(id=doc_id, **doc)


def get_db(cfg):
    wait_for_couchdb(cfg.couchdb_url)
    client = couchdb.client.Server(cfg.couchdb_url)
    try:
        return client.create('godhand')
    except couchdb.http.PreconditionFailed:
        return client['godhand']
