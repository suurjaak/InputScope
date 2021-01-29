# -*- mode: python -*-
"""
Pyinstaller spec file for InputScope, produces a Windows executable.

@author    Erki Suurjaak
@created   13.04.2015
@modified  29.01.2021
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
DATA_EXCLUDES = ["Include\\pyconfig.h"] # Workaround for PyInstaller 2.1 buggy warning about existing pyconfig.h
MODULE_EXCLUDES = ["_gtkagg", "_tkagg", "_tkinter", "bsddb", "bz2", "cherrypy",
                   "colorama", "curses", "distutils", "doctest", "FixTk", "gevent",
                   "html", "jinja2", "mako", "numpy", "OpenSSL", "os2emxpath",
                   "paste", "PIL", "pygments", "pywin", "servicemanager",
                   "setuptools", "sitecustomize", "tarfile", "tcl", "tk",
                   "Tkconstants", "tkinter", "Tkinter", "tornado", "unittest",
                   "urllib2", "win32ui", "wx.html", "xml", "xml.parsers.expat", ]
BINARY_EXCLUDES = ["_ssl", "_testcapi"]

a = Analysis([(os.path.join(APPPATH, "main.py"))], excludes=MODULE_EXCLUDES)
a.datas -= [(n, None, "DATA") for n in DATA_EXCLUDES] # entry=(name, path, typecode)
a.datas += [(os.path.join(*x), os.path.join(APPPATH, *x), "DATA")
            for x in APP_INCLUDES]
a.binaries -= [(n, None, None) for n in BINARY_EXCLUDES]
pyz = PYZ(a.pure)

exename = "%s_%s.exe" % (conf.Title, conf.Version)
exe = EXE(
    pyz,
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
