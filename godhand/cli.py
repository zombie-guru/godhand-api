import argparse
import json
import logging
import os
import sys

import couchdb.client
import couchdb.http

from .fuseclient import FuseClient
from .opendata import iterate_manga
from .config import GodhandConfiguration
from .utils import wait_for_couchdb
from .utils import batched


LOG = logging.getLogger(__file__)


def main():
    ap = argparse.ArgumentParser('godhand-cli')
    ap.add_argument('--log-level', default='DEBUG')
    s = ap.add_subparsers(dest='cmd')

    s.add_parser('dbpedia-dump')

    p = s.add_parser('upload')
    p.add_argument('--couchdb-url', default=None)
    p.add_argument('--fuse-url', default=None)

    p = s.add_parser('fuse-setup')
    p.add_argument('--fuse-url', default=None)

    p = s.add_parser('fuse-sync')
    p.add_argument('--couchdb-url', default=None)
    p.add_argument('--fuse-url', default=None)

    args = ap.parse_args()
    logging.basicConfig(
        level=args.log_level,
        format='%(asctime)s[%(name)s][%(levelname)s]: %(message)s',
    )
    if args.cmd == 'dbpedia-dump':
        dbpedia_dump()
    elif args.cmd == 'upload':
        upload(args.couchdb_url, args.fuse_url)
    elif args.cmd == 'fuse-setup':
        fuse_setup(args.fuse_url)
    elif args.cmd == 'fuse-sync':
        fuse_sync(args.couchdb_url, args.fuse_url)


def dbpedia_dump():
    for manga in iterate_manga():
        json.dump(manga, sys.stdout)
        sys.stdout.write('\n')


def upload(couchdb_url=None, fuse_url=None):
    cfg = GodhandConfiguration.from_env(
        books_path=os.path.abspath(os.path.curdir),
        couchdb_url=couchdb_url, fuse_url=fuse_url)
    db = get_db(cfg)
    for n_line, line in enumerate(sys.stdin):
        if n_line and (n_line % 100) == 0:
            LOG.info('uploaded {} documents'.format(n_line))
        doc = json.loads(line)
        doc['dbpedia_uri'] = doc.pop('uri')[0]
        keys = (
            'name', 'description', 'author', 'magazine', 'number_of_volumes')
        for key in keys:
            doc[key] = doc[key][0]
        doc['number_of_volumes'] = int(doc['number_of_volumes'])
        doc['genres'] = doc.pop('genre')
        doc['type'] = 'series'
        doc['volumes'] = []
        db.save(doc)


def fuse_setup(fuse_url=None):
    cfg = GodhandConfiguration.from_env(
        books_path=os.path.abspath(os.path.curdir),
        fuse_url=fuse_url, couchdb_url='http://couchdb')
    client = FuseClient(cfg.fuse_url)
    client.stop_fuse()
    client.setup_fuse()
    client.start_fuse()
    client.wait_until_ready()


def fuse_sync(couchdb_url=None, fuse_url=None):
    cfg = GodhandConfiguration.from_env(
        books_path=os.path.abspath(os.path.curdir),
        fuse_url=fuse_url, couchdb_url=couchdb_url)
    db = get_db(cfg)
    docs = db.query('''
    function(doc) {
        if ( (doc.type == "series") && (doc.volumes.length > 0)) {
            emit({
                _id: doc._id,
                name: doc.name,
                description: doc.description,
                genres: doc.genres,
                dbpedia_uri: doc.dbpedia_uri,
                author: doc.author,
                magazine: doc.magazine
            })
        }
    }
    ''')

    def to_fusedict(item):
        item = item.key
        item['fuse:id'] = item.pop('_id')
        item['fuse:type'] = 'series'
        return item

    client = FuseClient(cfg.fuse_url)
    for batch in batched(docs, 5000):
        batch = [to_fusedict(x) for x in batch]
        client.update(batch, index=True)


def get_db(cfg):
    wait_for_couchdb(cfg.couchdb_url)
    client = couchdb.client.Server(cfg.couchdb_url)
    try:
        return client.create('godhand')
    except couchdb.http.PreconditionFailed:
        return client['godhand']
