# -*- coding: utf-8 -*-
"""
Setup.py for InputScope.

@author      Erki Suurjaak
@created     29.04.2015
@modified    28.02.2022
------------------------------------------------------------------------------
"""
import os
import re
import sys
import setuptools

ROOTPATH  = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOTPATH, "src"))

from inputscope import conf


PACKAGE = conf.Title.lower()


def readfile(path):
    """Returns contents of path, relative to current file."""
    root = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(root, path)) as f: return f.read()

def get_description():
    """Returns package description from README."""
    LINK_RGX = r"\[([^\]]+)\]\(([^\)]+)\)"  # 1: content in [], 2: content in ()
    linkify = lambda s: "#" + re.sub(r"[^\w -]", "", s).lower().replace(" ", "-")
    # Unwrap local links like [Page link](#page-link) and [LICENSE.md](LICENSE.md)
    repl = lambda m: m.group(1 if m.group(2) in (m.group(1), linkify(m.group(1))) else 0)
    return re.sub(LINK_RGX, repl, readfile("README.md"))


setuptools.setup(
    name                 = conf.Title,
    version              = conf.Version,
    description          = "Mouse and keyboard input heatmap visualizer and statistics",
    url                  = "https://github.com/suurjaak/InputScope",

    author               = "Erki Suurjaak",
    author_email         = "erki@lap.ee",
    license              = "MIT",
    platforms            = ["any"],
    keywords             = "mouse keyboard logging heatmap",

    install_requires     = ["bottle", "pynput", "wxPython>=4.0"],
    entry_points         = {"gui_scripts": ["{0} = {0}.main:main".format(PACKAGE)],
                            "console_scripts": ["{0}-listener = {0}.listener:main".format(PACKAGE),
                                                "{0}-webui = {0}.webui:main".format(PACKAGE)]},

    package_dir          = {"": "src"},
    packages             = [PACKAGE],
    include_package_data = True, # Use MANIFEST.in for data files
    classifiers          = [
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

    long_description_content_type = "text/markdown",
    long_description = get_description(),
)
