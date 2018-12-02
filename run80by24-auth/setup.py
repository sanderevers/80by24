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
#with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
#    long_description = f.read()

setup(
    name='run80by24-auth',
    version='0.2.0',
    description='Authorization server for 80by24.',
#    long_description=long_description,
    url='https://80by24.net',
    author='Sander Evers',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='terminal console',
    packages=['run80by24.'+pkg for pkg in find_packages('run80by24')],
    install_requires=['Flask==1.0.2','Flask-SQLAlchemy==2.3.2','Authlib==0.10','requests==2.20.1','redis==3.0.1'],
    package_data={
         '': ['templates/*'],
    },

    entry_points={
    },
)