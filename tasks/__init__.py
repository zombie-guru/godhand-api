from invoke import Collection

from .build import ns as build
from .docs import ns as docs


ns = Collection()
ns.add_collection(build, name='build')
ns.add_collection(docs, name='docs')
