from setuptools import setup, find_packages

setup(
    name='godhand',
    version=0.1,
    description='godhand',
    classifiers=[],
    keywords="",
    author='',
    author_email='',
    url='',
    packages=find_packages(),
    package_data={
    },
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'cornice',
        'couchdb',
        'colander',
        'pyramid',
    ],
    entry_points={
        'paste.app_factory': [
            'main = godhand.rest:main',
        ],
        'console_scripts': [
        ]
    },
    extras_require={
        'tests': [
            'fixtures',
            'mock',
            'webtest',
        ],
        'docs': [
        ],
    }
)
