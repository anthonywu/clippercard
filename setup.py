from distutils.core import setup

setup(
    name='clippercard',
    version='0.1.1',
    author='Anthony Wu',
    author_email='anthonywu@systemfu.com',
    packages=['clippercard'],
    scripts=[],
    url='https://github.com/anthonywu/clippercard',
    license='LICENSE.txt',
    description='Unofficial Python API for Clipper Card (transportation pass used in the San Francisco Bay Area',
    long_description=open('README.txt').read(),
    install_requires=[
        "lxml",
        "pyquery",
        "requests"
    ],
)
