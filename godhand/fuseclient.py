from contextlib import contextmanager
from tempfile import TemporaryFile
from zipfile import ZipFile
import os
import time

import requests

here = os.path.dirname(__file__)
fusepkg_dir = os.path.join(here, 'fusepkg')


@contextmanager
def fusepkg():
    with TemporaryFile() as f:
        with ZipFile(f, mode='w') as z:
            for fn in ('contentschema.json', 'indexschema.json'):
                z.write(os.path.join(fusepkg_dir, fn), fn)
        f.flush()
        f.seek(0)
        yield f


class FuseClient(object):
    def __init__(self, baseurl):
        self.baseurl = baseurl
        self.s = requests.Session()

    def request(self, method, path, **kwargs):
        r = self.s.request(method, self.baseurl + path, **kwargs)
        r.raise_for_status()
        return r

    def update(self, items, index):
        r = self.request(
            'POST', '/tasks/types/update', json={'items': items},
            params={'index': index},
        )
        task_url = r.headers['location']
        status = self.wait_for_task(task_url)
        if index:
            self.wait_for_task(status['index_task']['@id'])

    def wait_for_task(self, task_url, n_tries=30, retry_rate=1):
        for _ in range(n_tries):
            status = self.get_task_status(task_url)
            if status['done']:
                return status
            time.sleep(retry_rate)
        raise RuntimeError('Timeout waiting for task: {!r}'.format(task_url))

    def get_task_status(self, task_url):
        r = self.s.get(task_url)
        r.raise_for_status()
        return r.json()

    def setup_fuse(self):
        self.wait_until_listening()
        with fusepkg() as pkg:
            self.request(
                'PUT', '/admin/instance',
                headers={'content-type': 'application/zip'},
                data=pkg,
            )

    def start_fuse(self):
        self.request('POST', '/admin/instance', json={'action': 'start'})

    def stop_fuse(self):
        self.request('POST', '/admin/instance', json={'action': 'stop'})

    def wait_until_listening(self, n_tries=30, retry_rate=1):
        for _ in range(n_tries):
            try:
                return self.get_status()
            except requests.exceptions.ConnectionError:
                time.sleep(retry_rate)
        raise RuntimeError('Timeout waiting for Fuse to be listening.')

    def wait_until_ready(self, n_tries=30, retry_rate=1):
        for _ in range(n_tries):
            if self.get_status()['ready']:
                return
            time.sleep(retry_rate)
        raise RuntimeError('Timeout waiting for Fuse to be ready.')

    def get_status(self):
        return self.request('GET', '/admin/instance').json()
