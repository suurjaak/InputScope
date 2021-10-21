# -*- coding: utf-8 -*-
"""
Setup.py for InputScope.

@author      Erki Suurjaak
@created     29.04.2015
@modified    21.10.2021
------------------------------------------------------------------------------
"""
import setuptools

from inputscope import conf

setuptools.setup(
    name=conf.Title,
    version=conf.Version,
    description="Mouse and keyboard input heatmap visualizer and statistics",
    url="https://github.com/suurjaak/InputScope",

    author="Erki Suurjaak",
    author_email="erki@lap.ee",
    license="MIT",
    platforms=["any"],
    keywords="mouse keyboard logging heatmap",

    install_requires=["bottle", "pynput", "wxPython>=4.0"],
    entry_points={"gui_scripts": ["inputscope = inputscope.main:main"],
                  "console_scripts": ["inputscope-listener = inputscope.listener:main",
                                      "inputscope-webui = inputscope.webui:main"]},

    packages=setuptools.find_packages(),
    include_package_data=True, # Use MANIFEST.in for data files
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Topic :: Desktop Environment",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],

    long_description_content_type="text/markdown",
    long_description=
"""Mouse and keyboard input heatmap visualizer and statistics.

Runs a tray program that logs mouse and keyboard input events to a local database,
and provides a local web page for viewing statistics and heatmaps by day or month.

Data is kept in an SQLite database.
""",
)
