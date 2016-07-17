import os
import re
import tarfile

ext_regex = re.compile('^.*\.(jpg|jpeg|gif|png|tiff)$', re.IGNORECASE)


def from_mimetype(mimetype):
    if mimetype == 'application/x-cbt':
        return CbtBookExtractor
    raise ValueError('Invalid mimetype for extraction: {!r}'.format(mimetype))


def from_filename(filename):
    filename = filename.lower()
    if filename.endswith('.cbt'):
        return CbtBookExtractor
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
    def __init__(self, f, path):
        """ Create a BookExtractor object.

        :param f: File pointer to book.
        :param path: Path to directory to extract to.
        """
        self.f = f
        self.path = path

    def extract(self):
        raise NotImplementedError()

    def iter_pages(self):
        self.extract()
        for root, dirs, files in os.walk(self.path):
            dirs.sort()
            files.sort()
            # ignore dot files
            files = filter(lambda x: not x.startswith('.'), files)
            for page in files:
                try:
                    mimetype = filename_to_mimetype(page)
                except ValueError:
                    continue
                relpath = os.path.relpath(
                    os.path.join(root, page),
                    self.path,
                )
                yield relpath, mimetype


class CbtBookExtractor(BookExtractor):
    def extract(self):
        with tarfile.open(fileobj=self.f) as ar:
            ar.extractall(self.path)
