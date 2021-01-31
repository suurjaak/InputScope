# -*- mode: python -*-
"""
Pyinstaller spec file for InputScope, produces a Windows executable.

@author    Erki Suurjaak
@created   13.04.2015
@modified  31.01.2021
"""
import os
import sys

APPPATH = os.path.join(os.path.dirname(os.path.abspath(SPEC)), "inputscope")
sys.path.append(APPPATH)
import conf


APP_INCLUDES = [("static", "icon.ico"),       ("static", "site.css"),
                ("static", "heatmap.min.js"), ("static", "keyboard.svg"),
                ("views", "index.tpl"),       ("views", "heatmap_keyboard.tpl"),
                ("views", "input.tpl"),       ("views", "heatmap_mouse.tpl"),
                ("views", "base.tpl"), ]
DATA_EXCLUDES = ["Include\\pyconfig.h"] # PyInstaller 2.1 bug: warning about existing pyconfig.h
MODULE_EXCLUDES = ["_gtkagg", "_tkagg", "_tkinter", "backports", "bsddb", "bz2",
                   "cherrypy", "colorama", "contextlib", "curses", "distutils",
                   "doctest", "email.errors", "email.feedparser", "email.header",
                   "email.message", "email.parser", "FixTk", "ftplib",
                   "future.backports", "future.builtins", "future.moves",
                   "future.types", "future.utils", "getpass", "gettext", "gevent",
                   "gzip", "html", "http", "jinja2", "mako", "multiprocessing.heap",
                   "multiprocessing.managers", "multiprocessing.pool",
                   "multiprocessing.reduction", "multiprocessing.sharedctypes",
                   "numpy", "OpenSSL", "optparse", "os2emxpath", "paste",
                   "paste.httpserver", "paste.translogger", "PIL", "pygments",
                   "pyreadline", "pywin", "servicemanager", "setuptools",
                   "sitecustomize", "sre", "tarfile", "tcl", "tk", "Tkconstants",
                   "tkinter", "Tkinter", "tornado", "unittest", "urllib2",
                   "win32com.client", "win32com.server", "win32ui", "wx.html",
                   "xml", "xml.parsers.expat", "xmllib", "xmlrpclib", "zipfile", ]
BINARY_EXCLUDES = ["_ssl", "_testcapi"]
PURE_RETAINS = {"encodings.": [
    "encodings.aliases", "encodings.ascii", "encodings.base64_codec",
    "encodings.hex_codec", "encodings.latin_1", "encodings.mbcs",
    "encodings.utf_8",
]}


a = Analysis([(os.path.join(APPPATH, "main.py"))], excludes=MODULE_EXCLUDES)
a.datas -= [(n, None, "DATA") for n in DATA_EXCLUDES] # entry=(name, path, typecode)
a.datas += [(os.path.join(*x), os.path.join(APPPATH, *x), "DATA")
            for x in APP_INCLUDES]
a.binaries -= [(n, None, None) for n in BINARY_EXCLUDES]
a.pure = TOC([(n, p, c) for (n, p, c) in a.pure if not any(
              n.startswith(k) and n not in vv for k, vv in PURE_RETAINS.items())])

exename = "%s_%s.exe" % (conf.Title, conf.Version)
exe = EXE(
    PYZ(a.pure),
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name=exename,
    debug=False,  # Verbose or non-verbose 
    strip=False,  # EXE and all shared libraries run through cygwin's strip, tends to render Win32 DLLs unusable
    upx=True,     # Using Ultimate Packer for eXecutables
    icon=os.path.join(APPPATH, "static", "icon.ico"),
    console=False # Use the Windows subsystem executable instead of the console one
)
