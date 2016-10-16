from shutil import rmtree

from invoke import Collection
from invoke import task


@task(name='clean')
def docs_clean(ctx):
    print('cleaning build folder')
    try:
        rmtree(ctx.docs.build_dir)
    except OSError:
        pass


@task(name='build', pre=(docs_clean,))
def docs_build(ctx):
    ctx.run('sphinx-build -v -W {src_dir} {build_dir}'.format(**ctx.docs))


@task(name='serve', default=True, pre=(docs_build,))
def docs_serve(ctx):
    ctx.run(
        'cd {build_dir} && python -m http.server {port}'.format(**ctx.docs),
        echo=True, hide='both')


ns = Collection(
    docs_build,
    docs_clean,
    docs_serve,
)
