from shutil import rmtree
import os

from invoke import Collection
from invoke import task

from .utils import BUILDOUT_DIRECTORY
from .utils import BUILDOUT_BIN_DIRECTORY


@task(name='clean')
def docs_clean(ctx):
    rmtree(ctx['docs']['build-dir'])


@task(name='build')
def docs_build(ctx):
    docs_clean(ctx)
    ctx.run('{} -v -W docs {}'.format(
        ctx['docs']['sphinx-bin'],
        ctx['docs']['build-dir'],
    ))


ns = Collection(
    docs_build,
    docs_clean,
)
ns.configure({
    'docs': {
        'sphinx-bin': os.path.join(BUILDOUT_BIN_DIRECTORY, 'sphinx-build'),
        'build-dir': os.path.join(BUILDOUT_DIRECTORY, 'build', 'docs'),
    }
})
