try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='clippercard',
    version='0.5.0',
    author='Your friendly neighborhood transit rider-hackers',
    author_email='goldengate88@systemfu.com',
    packages=['clippercard', 'tests'],
    package_dir={'clippercard': 'clippercard'},
    entry_points={
        'console_scripts': [
            'clippercard = clippercard.main:main',
        ]
    },
    scripts=[],
    url='https://github.com/clippercard/clippercard-python',
    license='MIT',
    description='Unofficial Python API for Clipper Card (transportation pass used in the San Francisco Bay Area)',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'BeautifulSoup4>=4.3.2',
        'configparser>=3.5.0,<4.0',
        'docopt>=0.6.1,<1.0',
        'PrettyTable>=0.7.2',
        'requests>=2.2.1,<3.0',
        'six>=1.12.0'
    ],
)
