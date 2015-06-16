# -*- mode: python -*-
"""
Pyinstaller spec file for InputScope, produces a Windows executable.

@author    Erki Suurjaak
@created   13.04.2015
@modified  21.05.2015
"""
import os
import sys

APPPATH = os.path.join(os.path.dirname(os.path.abspath(SPEC)), "inputscope")
sys.path.append(APPPATH)
import conf

a = Analysis([(os.path.join(APPPATH, "main.py"))],)
# Workaround for PyInstaller 2.1 buggy warning about existing pyconfig.h
for d in a.datas:
    if "pyconfig" in d[0]: 
        a.datas.remove(d)
        break
a.datas += [(os.path.join(*x), os.path.join(APPPATH, *x), "DATA") for x in
            (["static", "icon.ico"], ["static", "site.css"],
             ["static", "heatmap.min.js"], ["static", "keyboard.svg"],
             ["views", "base.tpl"], ["views", "heatmap.tpl"],
             ["views", "index.tpl"], ["views", "input.tpl"])]
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
