""" Tools to import metadata from open APIs.
"""
PREFIXES = {
    'http://dbpedia.org/resource/': 'dbr:',
}


def replace_uri_prefixes(uri):
    for k, v in PREFIXES.items():
        if uri.startswith(k):
            return uri.replace(k, v)
    raise ValueError('Unknown uri: {}'.format(uri))
