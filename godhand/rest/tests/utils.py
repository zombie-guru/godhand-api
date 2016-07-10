from tempfile import TemporaryFile
import contextlib
import os
import tarfile
import unittest

from fixtures import TempDir
from webtest import TestApp


class ApiTest(unittest.TestCase):
    maxDiff = 5000

    def setUp(self):
        from godhand.models import DB as db
        from godhand.rest import main
        base_path = self.use_fixture(TempDir()).path
        self.book_path = book_path = os.path.join(base_path, 'books')
        os.makedirs(book_path)
        sqlalchemy_url = 'sqlite:///{}'.format(os.path.join(base_path, 'db'))
        self.api = TestApp(main(
            {}, book_path=book_path, sqlalchemy_url=sqlalchemy_url))
        self.db = db

    def tearDown(self):
        self.db.remove()

    def use_fixture(self, fix):
        self.addCleanup(fix.cleanUp)
        fix.setUp()
        return fix


@contextlib.contextmanager
def tmp_cbt(filenames):
    with TemporaryFile() as f:
        with tarfile.open(fileobj=f, mode='w') as ar:
            for filename in filenames:
                with TemporaryFile() as mf:
                    content = 'content of {}'.format(filename).encode('utf-8')
                    mf.write(content)
                    mf.flush()
                    mf.seek(0)
                    info = tarfile.TarInfo(filename)
                    info.size = len(content)
                    ar.addfile(info, mf)
        f.flush()
        f.seek(0)
        yield f
