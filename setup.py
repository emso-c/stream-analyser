from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_desc = fh.read()

with open("requirements.txt") as f:
    requirements = [rq.replace("==", ">=") for rq in f.read().splitlines()]

setup(
    name="stream-analyser",
    version="v0.3.5",
    author="emso-c",
    author_email="emsoc192@gmail.com",
    description=("A tool that analyses live streams"),
    keywords=["youtube", "live", "stream", "chat", "highlight", "analysis"],
    url="https://github.com/emso-c/stream-analyser",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Environment :: Console",
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    entry_points={'console_scripts':[
        'streamanalyser = streamanalyser.modules.cli:main'
    ]},
    packages=find_packages(),
    package_dir={"": "."},
    python_requires=">=3.7",
    include_package_data=True,
    package_data={'streamanalyser': [
        'data/default_contexts.json',
        'data/keyword_filters.txt',
        'data/monogram_stop_punctuations.txt',
        'data/monogram_stop_words.txt',
        'fonts/NotoSansCJKjp-Bold.ttf',
        'requirements.txt',
    ]},
    install_requires=requirements,
)
