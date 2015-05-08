# -*- coding: utf-8 -*-
"""
InputScope main entrance, runs a tray application if wx available, a simple
command-line echoer otherwise. Launches the event listener and web UI server.

@author      Erki Suurjaak
@created     05.05.2015
@modified    04.05.2015
"""
import multiprocessing
import multiprocessing.forking
import os
import subprocess
import sys
import threading
import time
import webbrowser
try: import win32com.client # For creating startup shortcut
except ImportError: pass
tk = None
try: import wx, wx.lib.sized_controls, wx.py.shell
except ImportError:
    wx = None
    try: import Tkinter as tk   # For getting screen size if wx unavailable
    except ImportError: pass

import conf
import db
import listener
import webui

class Popen(multiprocessing.forking.Popen):
    """Support for PyInstaller-frozen Windows executables."""
    def __init__(self, *args, **kwargs):
        hasattr(sys, "frozen") and os.putenv("_MEIPASS2", sys._MEIPASS + os.sep)
        try: super(Popen, self).__init__(*args, **kwargs)
        finally: hasattr(sys, "frozen") and os.unsetenv("_MEIPASS2")

class Process(multiprocessing.Process): _Popen = Popen


class QueueLine(object):
    """Queue-like interface for writing lines to a file-like object."""
    def __init__(self, output): self.output = output
    def put(self, item): self.output.write("%s\n" % item)


class Model(threading.Thread):
    """Input monitor main runner model."""

    def __init__(self, messagehandler=None):
        """
        @param   messagehandler  function to invoke with incoming messages
        """
        threading.Thread.__init__(self)
        self.messagehandler = messagehandler
        self.running = False
        self.listenerqueue = None
        self.listener = None
        self.webui = None

    def toggle(self, input):
        if "mouse" == input:
            on = conf.MouseEnabled = not conf.MouseEnabled
        elif "keyboard" == input:
            on = conf.KeyboardEnabled = not conf.KeyboardEnabled
        conf.save()
        if self.listenerqueue:
            self.listenerqueue.put("%s_%s" % (input, "start" if on else "stop"))

    def stop(self):
        self.running = False
        self.listener and self.listenerqueue.put("exit")
        self.webui and self.webui.terminate()

    def log_resolution(self, size):
        if size: db.insert("screen_sizes", x=size[0], y=size[1])

    def run(self):
        if conf.Frozen:
            self.listenerqueue = multiprocessing.Queue()
            self.listener = Process(target=listener.start, args=(self.listenerqueue,))
            self.webui = Process(target=webui.start)
            self.listener.start(), self.webui.start()
        else:
            args = lambda *x: [sys.executable,
                   os.path.join(conf.ApplicationPath, x[0])] + list(x[1:])
            self.listener = subprocess.Popen(args("listener.py", "--quiet"),
                                             stdin=subprocess.PIPE)
            self.webui = subprocess.Popen(args("webui.py", "--quiet"))
            self.listenerqueue = QueueLine(self.listener.stdin)

        if conf.MouseEnabled:    self.listenerqueue.put("mouse_start")
        if conf.KeyboardEnabled: self.listenerqueue.put("keyboard_start")

        self.running = True
        while self.running: time.sleep(1)


class MainApp(getattr(wx, "App", object)):
    def OnInit(self):
        self.model = Model()
        self.startupservice = StartupService()

        self.frame_console = wx.py.shell.ShellFrame(None)
        self.trayicon = wx.TaskBarIcon()

        if os.path.exists(conf.IconPath):
            icons = wx.IconBundle()
            icons.AddIconFromFile(conf.IconPath, wx.BITMAP_TYPE_ICO)
            self.frame_console.SetIcons(icons)
            icon = (icons.GetIconOfExactSize((16, 16))
                    if "win32" == sys.platform else icons.GetIcon((24, 24)))
            self.trayicon.SetIcon(icon, conf.Title)

        self.frame_console.Title = "%s Console" % conf.Title

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_DISPLAY_CHANGED, self.OnDisplayChanged)
        self.trayicon.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnOpenUI)
        self.trayicon.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.OnOpenMenu)
        self.trayicon.Bind(wx.EVT_TASKBAR_RIGHT_DOWN, self.OnOpenMenu)
        self.frame_console.Bind(wx.EVT_CLOSE, self.OnToggleConsole)

        self.model.log_resolution(wx.GetDisplaySize())
        wx.CallAfter(self.model.start)
        return True # App.OnInit returns whether processing should continue


    def OnOpenMenu(self, event):
        """Creates and opens a popup menu for the tray icon."""
        menu, makeitem = wx.Menu(), lambda x, **k: wx.MenuItem(menu, -1, x, **k)
        item_ui       = makeitem("&Open statistics")
        item_startup  = makeitem("&Start with Windows",  kind=wx.ITEM_CHECK) \
                        if self.startupservice.can_start() else None
        item_mouse    = makeitem("Stop &mouse logging", kind=wx.ITEM_CHECK)
        item_keyboard = makeitem("Stop &keyboard logging", kind=wx.ITEM_CHECK)
        item_console  = makeitem("Show Python &console", kind=wx.ITEM_CHECK)
        item_exit     = makeitem("E&xit %s" % conf.Title)

        font = item_ui.Font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        item_ui.Font = font

        menu.AppendItem(item_ui)
        menu.AppendItem(item_startup) if item_startup else None
        menu.AppendSeparator()
        menu.AppendItem(item_mouse)
        menu.AppendItem(item_keyboard)
        menu.AppendSeparator()
        menu.AppendItem(item_console)
        menu.AppendItem(item_exit)

        if item_startup: item_startup.Check(self.startupservice.is_started())
        item_mouse.Check(not conf.MouseEnabled)
        item_keyboard.Check(not conf.KeyboardEnabled)
        item_console.Check(self.frame_console.Shown)

        menu.Bind(wx.EVT_MENU, self.OnOpenUI,         id=item_ui.GetId())
        menu.Bind(wx.EVT_MENU, self.OnToggleStartup,  id=item_startup.GetId()) \
        if item_startup else None
        menu.Bind(wx.EVT_MENU, self.OnToggleMouse,    id=item_mouse.GetId())
        menu.Bind(wx.EVT_MENU, self.OnToggleKeyboard, id=item_keyboard.GetId())
        menu.Bind(wx.EVT_MENU, self.OnToggleConsole,  id=item_console.GetId())
        menu.Bind(wx.EVT_MENU, self.OnClose,          id=item_exit.GetId())
        self.trayicon.PopupMenu(menu)


    def OnDisplayChanged(self, event=None):
        self.model.log_resolution(wx.GetDisplaySize())

    def OnOpenUI(self, event):
        webbrowser.open(conf.WebUrl)

    def OnToggleStartup(self, event):
        self.startupservice.stop() if self.startupservice.is_started() \
        else self.startupservice.start()

    def OnToggleMouse(self, event):
        self.model.toggle("mouse")

    def OnToggleKeyboard(self, event):
        self.model.toggle("keyboard")

    def OnToggleConsole(self, event):
        self.frame_console.Show(not self.frame_console.IsShown())

    def OnClose(self, event):
        self.model.stop(), self.trayicon.Destroy(), wx.Exit()


class StartupService(object):
    """
    Manages starting a program on system startup, if possible. Currently
    supports only Windows systems.
    """

    def can_start(self):
        """Whether startup can be set on this system at all."""
        return ("win32" == sys.platform)

    def is_started(self):
        """Whether the program has been added to startup."""
        return os.path.exists(self.get_shortcut_path())

    def start(self):
        """Sets the program to run at system startup."""
        shortcut_path = self.get_shortcut_path()
        target_path = conf.ExecutablePath
        workdir, icon = conf.ApplicationPath, conf.ShortcutIconPath
        self.create_shortcut(shortcut_path, target_path, workdir, icon)

    def stop(self):
        """Stops the program from running at system startup."""
        try: os.unlink(self.get_shortcut_path())
        except Exception: pass

    def get_shortcut_path(self):
        path = "~\\Start Menu\\Programs\\Startup\\%s.lnk" % conf.Title
        return os.path.expanduser(path)

    def create_shortcut(self, path, target="", workdir="", icon=""):
        if "url" == path[-3:].lower():
            with open(path, "w") as shortcut:
                shortcut.write("[InternetShortcut]\nURL=%s" % target)
        else:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(path)
            if target.lower().endswith(("py", "pyw")):
                # pythonw leaves no DOS window open
                python = sys.executable.replace("python.exe", "pythonw.exe")
                shortcut.Targetpath = '"%s"' % python
                shortcut.Arguments  = '"%s"' % target
            else:
                shortcut.Targetpath = target
            shortcut.WorkingDirectory = workdir
            if icon:
                shortcut.IconLocation = icon
            shortcut.save()


def main():
    """Program entry point."""
    conf.init(), db.init(conf.DbPath, conf.DbStatements)

    if wx:
        MainApp(redirect=True).MainLoop() # stdout/stderr directed to wx popup
    else:
        model = Model(lambda x: sys.stderr.write("\r%s" % x))
        if tk:
            widget = tk.Tk() # Use Tkinter instead to get screen size
            size = widget.winfo_screenwidth(), widget.winfo_screenheight()
            model.log_resolution(size)
        print("wxPython not available, using basic command line interface.")
        print("Web interface running at %s" % conf.WebUrl)
        try:
            model.run()
        except KeyboardInterrupt:
            model.stop()


if "__main__" == __name__:
    if conf.Frozen: multiprocessing.freeze_support()
    main()
