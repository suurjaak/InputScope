# -*- mode: python -*-
"""
Pyinstaller spec file for Inputscope, produces a 32-bit or 64-bit executable,
depending on Python environment.

Pyinstaller-provided names and variables: Analysis, EXE, PYZ, SPEC, TOC.

@author    Erki Suurjaak
@created   13.04.2015
@modified  29.07.2023
"""
import os
import struct
import sys

NAME        = "inputscope"
DO_DEBUGVER = False
DO_64BIT    = (struct.calcsize("P") * 8 == 64)

BUILDPATH = os.path.dirname(os.path.abspath(SPEC))
ROOTPATH  = BUILDPATH
APPPATH   = os.path.join(ROOTPATH, "src")
os.chdir(ROOTPATH)
sys.path.insert(0, APPPATH)

from inputscope import conf


APP_INCLUDES = [("static", "icon.ico"),       ("static", "site.css"),
                ("static", "heatmap.min.js"), ("static", "keyboard.svg"),
                ("views",  "index.tpl"),      ("static", "site.js"),
                ("views",  "input.tpl"),      ("views",  "heatmap.tpl"),
                ("views",  "base.tpl"),       ("views",  "session.tpl")]
DATA_EXCLUDES = ["Include\\pyconfig.h"] # PyInstaller 2.1 bug: warning about existing pyconfig.h
MODULE_EXCLUDES = ["_gtkagg", "_tkagg", "_tkinter", "backports", "bsddb", "bz2",
                   "cherrypy", "colorama", "curses", "distutils", "doctest",
                   "FixTk", "ftplib", "future.backports", "future.builtins", "future.moves",
                   "future.types", "future.utils", "getpass", "gettext", "gevent",
                   "gzip", "jinja2", "mako", "numpy", "OpenSSL", "optparse", "os2emxpath",
                   "paste", "paste.httpserver", "paste.translogger", "PIL", "pygments",
                   "pyreadline", "pywin", "servicemanager", "setuptools",
                   "sitecustomize", "sre", "tarfile", "tcl", "tk", "Tkconstants",
                   "tkinter", "Tkinter", "tornado", "unittest", "urllib2",
                   "win32com.server", "win32ui", "wx.html", "xml",
                   "xml.parsers.expat", "xmllib", "xmlrpclib", "zipfile", ]
MODULE_INCLUDES = ["pynput.mouse._win32", "pynput.keyboard._win32"]
BINARY_EXCLUDES = ["_ssl", "_testcapi"]
PURE_RETAINS = {"encodings.": [
    "encodings.aliases", "encodings.ascii", "encodings.base64_codec",
    "encodings.hex_codec", "encodings.latin_1", "encodings.mbcs",
    "encodings.utf_8",
]}


app_file = "%s_%s%s%s" % (NAME, conf.Version, "_x64" if DO_64BIT else "",
                          ".exe" if "nt" == os.name else "")
entrypoint = os.path.join(ROOTPATH, "launch.py")

with open(entrypoint, "w") as f:
    f.write("from %s import main; main.main()" % NAME)


a = Analysis(
    [entrypoint], excludes=MODULE_EXCLUDES, hiddenimports=MODULE_INCLUDES
)
a.datas -= [(n, None, "DATA") for n in DATA_EXCLUDES] # entry=(name, path, typecode)
a.datas += [(os.path.join(*x), os.path.join(APPPATH, NAME, *x), "DATA")
            for x in APP_INCLUDES]
a.binaries -= [(n, None, None) for n in BINARY_EXCLUDES]
a.pure = TOC([(n, p, c) for (n, p, c) in a.pure if not any(
              n.startswith(k) and n not in vv for k, vv in PURE_RETAINS.items())])
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts + ([("v", "", "OPTION")] if DO_DEBUGVER else []),
    a.binaries,
    a.datas,
    name=app_file,

    debug=DO_DEBUGVER, # Verbose or non-verbose debug statements printed
    exclude_binaries=False, # Binaries not left out of PKG
    strip=False, # EXE and all shared libraries run through cygwin's strip, tends to render Win32 DLLs unusable
    upx=True, # Using Ultimate Packer for eXecutables
    console=DO_DEBUGVER, # Use the Windows subsystem executable instead of the console one
    icon=os.path.join(APPPATH, NAME, "static", "icon.ico"),
)

try: os.remove(entrypoint)
except Exception: pass
