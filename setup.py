from setuptools import setup, find_packages

setup(
    name="riscos-dumpsprites",
    version="0.1.0",
    description="Display information about RISC OS sprite files",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Charles Ferguson",
    author_email="gerph@gerph.org",
    url="https://github.com/gerph/riscos-dumpsprite",
    packages=find_packages(exclude=["sprites*", "tests*"]),
    entry_points={
        "console_scripts": [
            "riscos-dumpsprites=riscos_dumpsprites.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
    ],
    python_requires=">=3.9",
)
