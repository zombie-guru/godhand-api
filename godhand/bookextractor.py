from contextlib import contextmanager
from shutil import rmtree
from tempfile import NamedTemporaryFile
from tempfile import mkdtemp
import os
import re
import subprocess
import tarfile
import zipfile

ext_regex = re.compile('^.*\.(jpg|jpeg|gif|png|tiff)$', re.IGNORECASE)


def from_mimetype(mimetype):
    if mimetype == 'application/x-cbt':
        return CbtBookExtractor
    raise ValueError('Invalid mimetype for extraction: {!r}'.format(mimetype))


def from_filename(filename):
    filename = filename.lower()
    if re.match('^.*\.(cbt|tgz|tar\.gz)$', filename, re.IGNORECASE):
        return CbtBookExtractor
    elif re.match('^.*\.(cbz|zip)$', filename, re.IGNORECASE):
        return CbzBookExtractor
    elif re.match('^.*\.(cbr|rar)$', filename, re.IGNORECASE):
        return CbrBookExtractor
    raise ValueError('Invalid filanem for extraction: {!r}'.format(filename))


def filename_to_mimetype(filename):
    ext = ext_regex.match(filename)
    if ext is None:
        raise ValueError('Invalid image filename: {!r}'.format(filename))
    ext = ext.group(1).lower()
    if ext in ('jpeg', 'jpg'):
        return 'images/jpeg'
    elif ext in ('png', 'gif'):
        return 'images/{}'.format(ext)


class BookExtractor(object):
    def __init__(self, f):
        """ Create a BookExtractor object.

        :param f: File pointer to book.
        :param path: Path to directory to extract to.
        """
        self.f = f

    def extract(self, tmp):
        raise NotImplementedError()

    @contextmanager
    def iter_pages(self):
        tmp = mkdtemp()
        yield self._iter_pages(tmp)
        rmtree(tmp)

    def _iter_pages(self, tmp):
        self.extract(tmp)
        for root, dirs, files in os.walk(tmp):
            files = filter(lambda x: not x.startswith('.'), files)
            for page in files:
                page = os.path.join(root, page)
                yield os.path.relpath(page, tmp), page


class CbtBookExtractor(BookExtractor):
    def extract(self, tmp):
        with tarfile.open(fileobj=self.f) as ar:
            ar.extractall(tmp)


class CbzBookExtractor(BookExtractor):
    def extract(self, tmp):
        with zipfile.ZipFile(self.f) as ar:
            ar.extractall(tmp)


class CbrBookExtractor(BookExtractor):
    def extract(self, tmp):
        with NamedTemporaryFile() as f:
            for line in self.f:
                f.write(line)
            f.flush()
            subprocess.check_call(['unrar', 'x', f.name, tmp])
