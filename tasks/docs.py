from shutil import rmtree

from invoke import Collection
from invoke import task


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
        'sphinx-bin': 'sphinx-build',
        'build-dir': 'build/docs',
    }
})
