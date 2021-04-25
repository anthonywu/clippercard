try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name="clippercard",
    version="202104.25.1",  # year/month, day, release of day
    author="Your friendly neighborhood transit rider-hackers",
    author_email="goldengate88@systemfu.com",
    packages=["clippercard", "tests"],
    package_dir={"clippercard": "clippercard"},
    entry_points={
        "console_scripts": [
            "clippercard = clippercard.main:main",
        ]
    },
    scripts=[],
    url="https://github.com/clippercard/clippercard-python",
    license="MIT",
    description="Unofficial Python API for Clipper Card (transportation pass used in the SF Bay Area)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=[
        "BeautifulSoup4>=4.9.0",
        "docopt>=0.6.1,<1.0",
        "PrettyTable>=2.1.0",
        "requests>=2.25.0,<3.0",
        "urllib3>=1.26.0"
    ],
    tests_require=[
        "pytest>=6.2.0",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
