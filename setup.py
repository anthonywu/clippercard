try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='clippercard',
    version='0.3.3',
    author='Anthony Wu',
    author_email='anthonywu@systemfu.com',
    packages=['clippercard'],
    package_dir = {'clippercard':'clippercard'},
    entry_points = {
        'console_scripts': [
            'clippercard = clippercard.main:main',
        ]
    },
    scripts=[],
    url='https://github.com/anthonywu/clippercard',
    license='LICENSE',
    description='Unofficial Python API for Clipper Card (transportation pass used in the San Francisco Bay Area)',
    long_description=open('README.rst').read(),
    install_requires=[
        'BeautifulSoup4 >= 4.3.2',
        'configparser == 3.5.0b2',
        'docopt >= 0.6.1',
        'prettytable >= 0.7.2',
        'requests >= 2.2.1'
    ],
)
