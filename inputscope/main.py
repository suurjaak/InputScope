# -*- coding: utf-8 -*-
"""
InputScope main entrance, runs a tray application if wx available, a simple
command-line echoer otherwise. Launches the event listener and web UI server.

@author      Erki Suurjaak
@created     05.05.2015
@modified    11.02.2021
"""
import calendar
import datetime
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
import urllib
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
        self.sizes = None # [[x, y, w, h], ]
        self.initialqueue = multiprocessing.Queue()
        self.listenerqueue = None
        self.listener = None
        self.webui = None
        # Avoid leaving zombie child processes on Ctrl-Break/C etc
        signal.signal(signal.SIGINT,   lambda *a, **kw: self.stop(True))
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, lambda *a, **kw: self.stop(True))


    def toggle(self, category):
        if category not in conf.InputFlags: return

        # Event input (mouse|keyboard), None if category itself is input
        input = next((k for k, vv in conf.InputEvents.items() if category in vv), None)
        attr = conf.InputFlags[category]
        on = not getattr(conf, attr)
        if input and not getattr(conf, conf.InputFlags[input]): # Event input itself off
            on = True # Force on regardless of event flag current state
            # Set other input events off, as only a single one was explicitly enabled
            for c, flag in ((c, conf.InputFlags[c]) for c in conf.InputEvents[input]):
                setattr(conf, flag, False)
        setattr(conf, attr, on)

        # Toggle input on when turning event category on
        if input and on: setattr(conf, conf.InputFlags[input], True)
        elif not any(getattr(conf, conf.InputFlags.get(c), False)
                     for c in conf.InputEvents[input or category]): # Not any event on
            if not input and on: # Turning input on
                # Toggle all input events on since all were off
                for c in conf.InputEvents[category]:
                    setattr(conf, conf.InputFlags[c], True)
            elif input and not on: # Turning single event off
                # Toggle entire input off since all input events are now off
                setattr(conf, conf.InputFlags[input], False)

        conf.save()
        q = self.listenerqueue or self.initialqueue
        q.put("%s %s" % ("start" if on else "stop", category))


    def stop(self, exit=False):
        self.running = False
        if self.listener: self.listenerqueue.put("exit"), self.listener.terminate()
        if self.webui: self.webui.terminate()
        if exit: sys.exit()

    def log_resolution(self, sizes):
        if sizes == self.sizes: return
        q = self.listenerqueue or self.initialqueue
        q.put("screen_size %s" % " ".join(map(str, sizes)))
        self.sizes = sizes

    def clear_history(self, category, dates):
        cmd = " ".join(["clear", category or "all"] + list(map(str, dates)))
        (self.listenerqueue or self.initialqueue).put(cmd)

    def vacuum(self):
        (self.listenerqueue or self.initialqueue).put("vacuum")

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

        if conf.MouseEnabled:    self.listenerqueue.put("start mouse")
        if conf.KeyboardEnabled: self.listenerqueue.put("start keyboard")
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
        self.icons = None
        self.sizetimer = wx.Timer(self)

        if os.path.exists(conf.IconPath):
            icons = self.icons = wx.IconBundle()
            icons.AddIcon(conf.IconPath, wx.BITMAP_TYPE_ICO)
            self.frame_console.SetIcons(icons)
            icon = (icons.GetIconOfExactSize((16, 16))
                    if "win32" == sys.platform else icons.GetIcon((24, 24)))
            self.trayicon.SetIcon(icon, conf.Title)

        self.frame_console.Title = "%s Console" % conf.Title

        self.Bind(wx.EVT_CLOSE,                            self.OnClose)
        self.Bind(wx.EVT_DISPLAY_CHANGED,                  self.OnLogResolution)
        self.Bind(wx.EVT_TIMER,                            self.OnLogResolution)
        self.trayicon.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.OnOpenUI)
        self.trayicon.Bind(wx.adv.EVT_TASKBAR_RIGHT_DOWN,  self.OnOpenMenu)
        self.frame_console.Bind(wx.EVT_CLOSE,              self.OnToggleConsole)

        def after():
            if not self: return
            self.OnLogResolution()
            self.model.start()
            msg = "Logging %s." % ("\nand ".join(filter(bool,
                  ["%s inputs (%s)" % (i, ", ".join(c for c in conf.InputEvents[i]
                                             if getattr(conf, conf.InputFlags[c])))
                  for i in conf.InputEvents if getattr(conf, conf.InputFlags[i])]))
                  if conf.MouseEnabled or conf.KeyboardEnabled else "no inputs")
            self.trayicon.ShowBalloon(conf.Title, msg)
            self.sizetimer.Start(conf.ScreenSizeInterval * 1000)


        wx.CallAfter(after)
        return True # App.OnInit returns whether processing should continue


    def OnOpenMenu(self, event):
        """Creates and opens a popup menu for the tray icon."""
        menu, makeitem = wx.Menu(), lambda m, x, **k: wx.MenuItem(m, -1, x, **k)
        mousemenu, keyboardmenu, histmenu = wx.Menu(), wx.Menu(), wx.Menu()
        histall_menu, histday_menu, histmon_menu, histdts_menu = wx.Menu(), wx.Menu(), wx.Menu(), wx.Menu()
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

        item_vacuum   = makeitem(histmenu, "&Repack database to smaller size")

        for m in histall_menu, histmon_menu, histday_menu, histdts_menu:
            item_all = makeitem(m, "All inputs")
            period = "all" if m is histall_menu else "month" if m is histmon_menu else \
                     "today" if m is histday_menu else "range"
            m.Bind(wx.EVT_MENU, functools.partial(self.OnClearHistory, period, None),
                   id=item_all.GetId())
            m.Append(item_all)
            for input, cc in conf.InputTables:
                item_input = makeitem(m, "    %s inputs" % input.capitalize())
                m.Bind(wx.EVT_MENU, functools.partial(self.OnClearHistory, period, input),
                       id=item_input.GetId())
                m.Append(item_input)
                for c in cc:
                    item_cat = makeitem(m, "        %s" % c)
                    m.Bind(wx.EVT_MENU, functools.partial(self.OnClearHistory, period, c),
                           id=item_cat.GetId())
                    m.Append(item_cat)
        histmenu.AppendSubMenu(histall_menu, "Clear &all history")
        histmenu.AppendSubMenu(histmon_menu, "Clear this &month")
        histmenu.AppendSubMenu(histday_menu, "Clear &today")
        histmenu.AppendSubMenu(histdts_menu, "Clear history &from .. to ..")
        histmenu.AppendSeparator()
        histmenu.Append(item_vacuum)

        item_ui.Font = item_ui.Font.Bold()

        mousemenu.Append(item_moves)
        mousemenu.Append(item_clicks)
        mousemenu.Append(item_scrolls)
        keyboardmenu.Append(item_keys)
        keyboardmenu.Append(item_combos)

        menu.Append(item_ui)
        menu.Append(item_startup) if item_startup else None
        menu.AppendSeparator()
        menu.Append(item_mouse)
        menu.AppendSubMenu(mousemenu, "  Mouse &event categories")
        menu.Append(item_keyboard)
        menu.AppendSubMenu(keyboardmenu, "  Keyboard e&vent categories")
        menu.AppendSeparator()
        menu.AppendSubMenu(histmenu, "Clear events &history")
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
        menu.Bind(wx.EVT_MENU, self.OnVacuum,           id=item_vacuum.GetId())
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


    def OnClearHistory(self, period, category, event=None):
        """Handler for clicking a clear menu item, forwards command to listener."""
        input = next((k for k, vv in conf.InputEvents.items() if category in vv), None)
        label = "%s %s" % (input, category) if input else "%s inputs" % (category or "all")
        dates = []
        if "range" == period:
            for dtlabel in ("start", "end"):
                v = ""
                while not isinstance(v, datetime.date):
                    dlg = wx.TextEntryDialog(None, "Enter %s date as YYYY-MM-DD:" % dtlabel,
                                             "Clear %s" % label, value=v, style=wx.OK | wx.CANCEL)
                    if self.icons: dlg.SetIcons(self.icons)
                    dlg.CenterOnScreen()
                    if wx.ID_OK != dlg.ShowModal(): return
                    v = dlg.GetValue().strip()
                    try: v = datetime.datetime.strptime(v, "%Y-%m-%d").date()
                    except Exception: continue # while not isinstance(v, datetime.date)
                    dates.append(v)

        else:
            tperiod = "this month's" if "month" == period else "today's" if "today" == period \
                      else period
            msg = "Are you sure you want to clear %s history of %s? This may take a while." % (tperiod, label)
            if wx.OK != wx.MessageBox(msg, conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING): return
            if "today" == period: dates = [datetime.date.today()] * 2
            elif "month" == period:
                day = datetime.date.today()
                _, last = calendar.monthrange(*day.timetuple()[:2])
                dates.extend([day.replace(day=1), day.replace(day=last)])
        self.model.clear_history(category, dates)


    def OnLogResolution(self, event=None):
        if not self: return
        sizes = [list(wx.Display(i).Geometry)
                 for i in range(wx.Display.GetCount())]
        self.model.log_resolution(sizes)

    def OnOpenUI(self, event):
        webbrowser.open(conf.WebUrl)

    def OnVacuum(self, event):
        msg = "Are you sure you want to repack the database? This may take a while."
        if wx.OK != wx.MessageBox(msg, conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING): return
        self.model.vacuum()

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
        name = urllib.quote_plus("-".join([conf.Title, conf.DbPath]))
        singlechecker = wx.SingleInstanceChecker(name)
        if singlechecker.IsAnotherRunning(): sys.exit()

        app = MainApp(redirect=True) # redirect stdout/stderr to wx popup
        locale = wx.Locale(wx.LANGUAGE_ENGLISH) # Avoid dialog buttons in native language
        app.MainLoop() # stdout/stderr directed to wx popup
    else:
        model = Model()
        if tk:
            widget = tk.Tk() # Use Tkinter instead to get screen size
            size = [0, 0, widget.winfo_screenwidth(), widget.winfo_screenheight()]
            model.log_resolution([size])
            widget.destroy()
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
