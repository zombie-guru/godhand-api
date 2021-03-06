from itertools import islice
from subprocess import check_call
import argparse
import json
import logging
import sys

import couchdb.client
import couchdb.http

from .config import GodhandConfiguration
from .models import Series
from .models import Volume
from .utils import wait_for_couchdb

LOG = logging.getLogger(__file__)
PREFIXES = {
    'http://dbpedia.org/resource/': 'dbr:',
}


def replace_uri_prefixes(uri):
    for k, v in PREFIXES.items():
        if uri.startswith(k):
            return uri.replace(k, v)
    raise ValueError('Unknown uri: {}'.format(uri))


def main():
    ap = argparse.ArgumentParser('godhand-cli')
    ap.add_argument('--log-level', default='DEBUG')
    s = ap.add_subparsers(dest='cmd')

    s.add_parser('api')
    s.add_parser('worker')

    s.add_parser('dbpedia-dump')

    p = s.add_parser('upload')
    p.add_argument('--couchdb-url', default=None)

    p = s.add_parser('update-user')
    p.add_argument('--couchdb-url', default=None)
    p.add_argument('user')
    p.add_argument('groups', nargs='+', default=['user'])

    args = ap.parse_args()
    logging.basicConfig(
        level=args.log_level,
        format='%(asctime)s[%(name)s][%(levelname)s]: %(message)s',
    )
    if args.cmd == 'api':
        check_call(['pserve', 'app.ini'])
    elif args.cmd == 'upload':
        upload(args.couchdb_url)


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
    Series.by_name.sync(db)
    Volume.by_series.sync(db)


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


def get_db(cfg, db='godhand'):
    wait_for_couchdb(cfg.couchdb_url)
    client = couchdb.client.Server(cfg.couchdb_url)
    try:
        return client.create(db)
    except couchdb.http.PreconditionFailed:
        return client[db]
