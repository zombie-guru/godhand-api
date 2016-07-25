from shutil import rmtree

from invoke import Collection
from invoke import task
from invoke import run


@task(name='clean')
def build_clean(ctx):
    rmtree('dist')


@task(name='wheel')
def build_wheel(ctx):
    run('python3 setup.py bdist_wheel')


@task(name='image')
def build_image(ctx):
    run('docker build -t {} .'.format(ctx['build']['docker-repo']))


@task(name='all', default=True)
def build_all(ctx):
    build_clean(ctx)
    build_wheel(ctx)
    build_image(ctx)


ns = Collection(
    build_clean,
    build_wheel,
    build_image,
    build_all,
)
ns.configure({
    'build': {
        'docker-repo': 'zombieguru/godhand',
    }
})
