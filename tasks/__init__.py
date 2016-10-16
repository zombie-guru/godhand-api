from invoke import Collection
from .docs import ns as docs


ns = Collection()
ns.add_collection(docs, name='docs')
ns.configure({
    'docs': {
        'build_dir': 'build/docs',
        'src_dir': 'docs',
        'port': '8000',
    },
})
