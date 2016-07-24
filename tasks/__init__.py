from invoke import Collection

from .docs import ns as docs


ns = Collection()
ns.add_collection(docs, name='docs')
