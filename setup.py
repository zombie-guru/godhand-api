from setuptools import setup, find_packages

setup(
    name='godhand',
    version=0.1,
    description='godhand',
    classifiers=[],
    keywords='',
    author='Geoffrey Chan',
    author_email='geoffrey@zombie.guru',
    url='',
    packages=find_packages(),
    package_data={},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'cornice',
        'couchdb',
        'colander',
        'oauth2client',
        'Pillow',
        'PyJWT',
        'pyramid',
        'requests',
        'sparqlwrapper',
    ],
    entry_points={
        'paste.app_factory': [
            'main = godhand.rest:main',
        ],
        'console_scripts': [
            'godhand-cli = godhand.cli:main',
        ]
    },
    extras_require={
        'tests': [
            'mock',
            'webtest',
        ],
        'docs': [
        ],
    }
)
