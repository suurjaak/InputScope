# -*- coding: utf-8 -*-
"""
InputScope main entrance, runs a tray application if wx available, a simple
command-line echoer otherwise. Launches the event listener and web UI server.

@author      Erki Suurjaak
@created     05.05.2015
@modified    24.01.2021
"""
import errno
import functools
import multiprocessing
import multiprocessing.forking
import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
try: import win32com.client # For creating startup shortcut
except ImportError: pass
wx = tk = None
try: import wx, wx.adv, wx.py.shell
except ImportError:
    try: import Tkinter as tk   # For getting screen size if wx unavailable
    except ImportError: pass

import conf
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
    def put(self, item):
        try: self.output.write("%s\n" % item)
        except IOError as e:
            if e.errno != errno.EINVAL: raise # Invalid argument, probably stale pipe


class Model(threading.Thread):
    """Input monitor main runner model."""

    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        self.initialqueue = multiprocessing.Queue()
        self.listenerqueue = None
        self.listener = None
        self.webui = None
        # Avoid leaving zombie child processes on Ctrl-Break/C etc
        signal.signal(signal.SIGBREAK, lambda *a, **kw: self.stop(True))
        signal.signal(signal.SIGINT,   lambda *a, **kw: self.stop(True))

    def toggle(self, category):
        if category not in conf.InputFlags: return

        input = next((k for k, vv in conf.InputEvents.items() if category in vv), None)
        attr = conf.InputFlags[category]
        on = not getattr(conf, attr)
        if input and not getattr(conf, conf.InputFlags[input]):
            on = True # Force on, as event checkboxes are always off if input is off
            # Set other input categories off, as only a single one was enabled
            for c, flag in ((c, conf.InputFlags[c]) for c in conf.InputEvents[input]):
                setattr(conf, flag, False)
        setattr(conf, attr, on)
        if input and on: setattr(conf, conf.InputFlags[input], True)
        elif input and not any(getattr(conf, conf.InputFlags.get(c), False)
                               for c in conf.InputEvents[input]):
            # Toggle entire input off if all event categories are now off
            setattr(conf, conf.InputFlags[input], False)

        conf.save()
        if self.listenerqueue:
            self.listenerqueue.put("%s_%s" % (category, "start" if on else "stop"))

    def stop(self, exit=False):
        self.running = False
        if self.listener: self.listenerqueue.put("exit"), self.listener.terminate()
        if self.webui: self.webui.terminate()
        if exit: sys.exit()

    def log_resolution(self, size):
        q = self.listenerqueue or self.initialqueue
        q.put("screen_size %s %s" % (size[0], size[1]))

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
        for category, flag in conf.InputFlags.items():
            if category not in conf.InputEvents \
            and hasattr(conf, flag) and not getattr(conf, flag):
                self.listenerqueue.put("%s_stop" % category)
        while not self.initialqueue.empty():
            self.listenerqueue.put(self.initialqueue.get())

        self.running = True
        while self.running: time.sleep(1)


class MainApp(getattr(wx, "App", object)):
    def OnInit(self):
        self.model = Model()
        self.startupservice = StartupService()

        self.frame_console = wx.py.shell.ShellFrame(None)
        self.trayicon = wx.adv.TaskBarIcon()

        if os.path.exists(conf.IconPath):
            icons = wx.IconBundle()
            icons.AddIcon(conf.IconPath, wx.BITMAP_TYPE_ICO)
            self.frame_console.SetIcons(icons)
            icon = (icons.GetIconOfExactSize((16, 16))
                    if "win32" == sys.platform else icons.GetIcon((24, 24)))
            self.trayicon.SetIcon(icon, conf.Title)

        self.frame_console.Title = "%s Console" % conf.Title

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_DISPLAY_CHANGED, self.OnDisplayChanged)
        self.trayicon.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.OnOpenUI)
        self.trayicon.Bind(wx.adv.EVT_TASKBAR_RIGHT_DOWN, self.OnOpenMenu)
        self.frame_console.Bind(wx.EVT_CLOSE, self.OnToggleConsole)


        def after():
            if not self: return
            self.model.log_resolution(wx.GetDisplaySize())
            self.model.start()
            msg = "Logging %s." % ("\nand ".join(filter(bool,
                  ["%s inputs (%s)" % (i, ", ".join(c for c in conf.InputEvents[i]
                                             if getattr(conf, conf.InputFlags[c])))
                  for i in conf.InputEvents if getattr(conf, conf.InputFlags[i])]))
                  if conf.MouseEnabled or conf.KeyboardEnabled else "no inputs")
            self.trayicon.ShowBalloon(conf.Title, msg)
            

        wx.CallAfter(after)
        return True # App.OnInit returns whether processing should continue


    def OnOpenMenu(self, event):
        """Creates and opens a popup menu for the tray icon."""
        menu, makeitem = wx.Menu(), lambda m, x, **k: wx.MenuItem(m, -1, x, **k)
        mousemenu, keyboardmenu = wx.Menu(), wx.Menu()
        on_category = lambda c: functools.partial(self.OnToggleCategory, c)
        item_ui       = makeitem(menu, "&Open statistics")
        item_startup  = makeitem(menu, "Start with &Windows",  kind=wx.ITEM_CHECK) \
                        if self.startupservice.can_start() else None
        item_mouse    = makeitem(menu, "Enable &mouse logging",    kind=wx.ITEM_CHECK)
        item_keyboard = makeitem(menu, "Enable &keyboard logging", kind=wx.ITEM_CHECK)
        item_console  = makeitem(menu, "Show Python &console",     kind=wx.ITEM_CHECK)
        item_exit     = makeitem(menu, "E&xit %s" % conf.Title)

        item_moves    = makeitem(mousemenu,    "Log mouse &movement",   kind=wx.ITEM_CHECK)
        item_clicks   = makeitem(mousemenu,    "Log mouse &clicks",     kind=wx.ITEM_CHECK)
        item_scrolls  = makeitem(keyboardmenu, "Log mouse &scrolls",    kind=wx.ITEM_CHECK)
        item_keys     = makeitem(keyboardmenu, "Log individual &keys",  kind=wx.ITEM_CHECK)
        item_combos   = makeitem(keyboardmenu, "Log key &combinations", kind=wx.ITEM_CHECK)

        font = item_ui.Font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        item_ui.Font = font

        mousemenu.Append(item_moves)
        mousemenu.Append(item_clicks)
        mousemenu.Append(item_scrolls)
        keyboardmenu.Append(item_keys)
        keyboardmenu.Append(item_combos)

        menu.Append(item_ui)
        menu.Append(item_startup) if item_startup else None
        menu.AppendSeparator()
        menu.Append(item_mouse)
        menu.AppendSubMenu(mousemenu,    "  Mouse &event categories")
        menu.Append(item_keyboard)
        menu.AppendSubMenu(keyboardmenu, "  Keyboard event &categories")
        menu.AppendSeparator()
        menu.Append(item_console)
        menu.Append(item_exit)

        if item_startup: item_startup.Check(self.startupservice.is_started())
        item_mouse   .Check(conf.MouseEnabled)
        item_moves   .Check(conf.MouseEnabled and conf.MouseMovesEnabled)
        item_clicks  .Check(conf.MouseEnabled and conf.MouseClicksEnabled)
        item_scrolls .Check(conf.MouseEnabled and conf.MouseScrollsEnabled)
        item_keyboard.Check(conf.KeyboardEnabled)
        item_keys    .Check(conf.KeyboardEnabled and conf.KeyboardKeysEnabled)
        item_combos  .Check(conf.KeyboardEnabled and conf.KeyboardCombosEnabled)
        item_console .Check(self.frame_console.Shown)

        menu.Bind(wx.EVT_MENU, self.OnOpenUI,           id=item_ui.GetId())
        menu.Bind(wx.EVT_MENU, self.OnToggleStartup,    id=item_startup.GetId()) \
        if item_startup else None
        menu.Bind(wx.EVT_MENU, on_category("mouse"),    id=item_mouse.GetId())
        menu.Bind(wx.EVT_MENU, on_category("keyboard"), id=item_keyboard.GetId())
        menu.Bind(wx.EVT_MENU, on_category("moves"),    id=item_moves.GetId())
        menu.Bind(wx.EVT_MENU, on_category("clicks"),   id=item_clicks.GetId())
        menu.Bind(wx.EVT_MENU, on_category("scrolls"),  id=item_scrolls.GetId())
        menu.Bind(wx.EVT_MENU, on_category("keys"),     id=item_keys.GetId())
        menu.Bind(wx.EVT_MENU, on_category("combos"),   id=item_combos.GetId())
        menu.Bind(wx.EVT_MENU, self.OnToggleConsole,    id=item_console.GetId())
        menu.Bind(wx.EVT_MENU, self.OnClose,            id=item_exit.GetId())
        self.trayicon.PopupMenu(menu)


    def OnDisplayChanged(self, event=None):
        self.model.log_resolution(wx.GetDisplaySize())

    def OnOpenUI(self, event):
        webbrowser.open(conf.WebUrl)

    def OnToggleStartup(self, event):
        self.startupservice.stop() if self.startupservice.is_started() \
        else self.startupservice.start()

    def OnToggleCategory(self, category, event):
        self.model.toggle(category)

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
        except StandardError: pass

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
    conf.init()

    if wx:
        MainApp(redirect=True).MainLoop() # stdout/stderr directed to wx popup
    else:
        model = Model()
        if tk:
            widget = tk.Tk() # Use Tkinter instead to get screen size
            size = widget.winfo_screenwidth(), widget.winfo_screenheight()
            model.log_resolution(size)
        print("wxPython not available, using basic command line interface.")
        print("Web interface running at %s" % conf.WebUrl)
        try:
            model.run()
        except IOError as e:
            if e.errno != errno.EINTR: raise # Interrupted syscall, probably sleep
        except KeyboardInterrupt:
            model.stop()


if "__main__" == __name__:
    if conf.Frozen: multiprocessing.freeze_support()
    main()
