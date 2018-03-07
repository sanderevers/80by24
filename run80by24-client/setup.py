"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='run80by24-client',
    version='0.2.0',
    description='Client for publishing to text terminals over HTTP.',
    long_description=long_description,
    url='https://80by24.net',
    author='Sander Evers',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3.4',
    ],

    keywords='terminal console',
    packages=['run80by24.'+pkg for pkg in find_packages('run80by24')],
    install_requires=['pyyaml','websockets','run80by24-common==0.2.0'],
    # package_data={  # Optional
    #     'sample': ['package_data.dat'],
    # },

    entry_points={
        'console_scripts': [
            '80by24=run80by24.client.__main__:main',
        ],
    },
)