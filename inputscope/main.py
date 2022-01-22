# -*- coding: utf-8 -*-
"""
InputScope main entrance, runs a tray application if wx available, a simple
command-line echoer otherwise. Launches the event listener and web UI server.

@author      Erki Suurjaak
@created     05.05.2015
@modified    21.10.2021
"""
import calendar
import datetime
import errno
import functools
import multiprocessing
import os
import re
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

from . import conf
from . import db
from . import listener
from . import webui
from . util import QueueLine, format_session, run_later


try: # Py2
    import multiprocessing.forking

    class Popen(multiprocessing.forking.Popen):
        """Support for PyInstaller-frozen Windows executables."""
        def __init__(self, *args, **kwargs):
            hasattr(sys, "frozen") and os.putenv("_MEIPASS2", sys._MEIPASS + os.sep)
            try: super(Popen, self).__init__(*args, **kwargs)
            finally: hasattr(sys, "frozen") and os.unsetenv("_MEIPASS2")

    class Process(multiprocessing.Process): _Popen = Popen
except ImportError: # Py3
    class Process(multiprocessing.Process): pass


class Model(threading.Thread):
    """Input monitor main runner model."""

    def __init__(self):
        threading.Thread.__init__(self)
        self.running = False
        self.sessions = []
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
        """Toggles logging input category on or off."""
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


    def session_action(self, action, session=None, arg=None):
        """Carries out session action."""
        q = self.listenerqueue or self.initialqueue
        q.put(" ".join(filter(bool, ("session", action, arg, session and str(session["id"])))))
        if action in ("rename", "delete", "start", "stop"):
            run_later(lambda: setattr(self, "sessions", db.fetch("sessions", order="start DESC")), 1000)

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
            pkg = os.path.basename(conf.ApplicationPath)
            root = os.path.dirname(conf.ApplicationPath)
            args = lambda *x: [sys.executable, "-m", "%s.%s" % (pkg, x[0])] + list(x[1:])
            self.listener = subprocess.Popen(args("listener", "--quiet"), cwd=root, shell=True,
                                             stdin=subprocess.PIPE, universal_newlines=True)
            self.webui = subprocess.Popen(args("webui", "--quiet"), cwd=root)
            self.listenerqueue = QueueLine(self.listener.stdin)

        if conf.MouseEnabled:    self.listenerqueue.put("start mouse")
        if conf.KeyboardEnabled: self.listenerqueue.put("start keyboard")
        while not self.initialqueue.empty():
            self.listenerqueue.put(self.initialqueue.get())

        self.sessions = db.fetch("sessions", order="start DESC")

        self.running = True
        while self.running: time.sleep(1)


class MainApp(getattr(wx, "App", object)):

    def InitLocale(self):
        # Avoid dialog buttons in native language
        pass

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
        sessions_menu = wx.Menu()
        histall_menu, histmon_menu, histday_menu = wx.Menu(), wx.Menu(), wx.Menu()
        histdts_menu, histses_menu = wx.Menu(), wx.Menu()
        on_category = lambda c: functools.partial(self.OnToggleCategory, c)
        on_session  = lambda k, s=None: functools.partial(self.OnSessionAction, k, session=s)
        on_clear    = lambda p, c, s=False: functools.partial(self.OnSessionAction, "clear", category=c) \
                                            if s else functools.partial(self.OnClearHistory, p, c)

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

        lastsession = self.model.sessions[0] if self.model.sessions else None
        activesession = lastsession if lastsession and not lastsession["end"] else None
        activename = format_session(activesession, quote=True, stamp=False) if activesession else None
        item_session_start = makeitem(menu, "&Start session ..")
        item_session_stop  = makeitem(menu, "Stop session%s" % (' ' + activename if activename else ""))
        item_session_stop.Enable(bool(activename))
        for session in self.model.sessions[:conf.MaxSessionsInMenu]:
            sessmenu = wx.Menu()
            item_session_open   = makeitem(sessmenu, "Open statistics")
            item_session_rename = makeitem(sessmenu, "Rename")
            item_session_clear  = makeitem(sessmenu, "Clear events")
            item_session_delete = makeitem(sessmenu, "Delete")
            sessmenu.Bind(wx.EVT_MENU, on_session("open",   session), item_session_open)
            sessmenu.Bind(wx.EVT_MENU, on_session("rename", session), item_session_rename)
            sessmenu.Bind(wx.EVT_MENU, on_session("clear",  session), item_session_clear)
            sessmenu.Bind(wx.EVT_MENU, on_session("delete", session), item_session_delete)
            sessmenu.Append(item_session_open)
            sessmenu.Append(item_session_rename)
            sessmenu.Append(item_session_clear)
            sessmenu.Append(item_session_delete)
            sessions_menu.AppendSubMenu(sessmenu, format_session(session))

        item_vacuum = makeitem(histmenu, "&Repack database to smaller size")

        for m in histall_menu, histmon_menu, histday_menu, histdts_menu, histses_menu:
            item_all = makeitem(m, "All inputs")
            period = "all" if m in (histall_menu, histses_menu) else \
                     "month" if m is histmon_menu else "today" if m is histday_menu else "range"
            session = (m is histses_menu)
            m.Bind(wx.EVT_MENU, on_clear(period, None, session), id=item_all.GetId())
            m.Append(item_all)
            for input, cc in conf.InputTables:
                item_input = makeitem(m, "    %s inputs" % input.capitalize())
                m.Bind(wx.EVT_MENU, on_clear(period, input, session), id=item_input.GetId())
                m.Append(item_input)
                for c in cc:
                    item_cat = makeitem(m, "        %s" % c)
                    m.Bind(wx.EVT_MENU, on_clear(period, c, session), id=item_cat.GetId())
                    m.Append(item_cat)
        histmenu.AppendSubMenu(histall_menu, "Clear &all history")
        histmenu.AppendSubMenu(histmon_menu, "Clear this &month")
        histmenu.AppendSubMenu(histday_menu, "Clear &today")
        histmenu.AppendSubMenu(histdts_menu, "Clear history &from .. to ..")
        item_sessions_clear = histmenu.AppendSubMenu(histses_menu, "Clear from &session ..")
        histmenu.Enable(item_sessions_clear.Id, bool(self.model.sessions))
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
        menu.Append(item_session_start)
        menu.Append(item_session_stop)
        item_sessions = menu.AppendSubMenu(sessions_menu, "Sessions")
        menu.Enable(item_sessions.Id, bool(self.model.sessions))
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

        menu.Bind(wx.EVT_MENU, self.OnOpenUI,           item_ui)
        menu.Bind(wx.EVT_MENU, self.OnVacuum,           item_vacuum)
        menu.Bind(wx.EVT_MENU, self.OnToggleStartup,    item_startup) if item_startup else None
        menu.Bind(wx.EVT_MENU, on_category("mouse"),    item_mouse)
        menu.Bind(wx.EVT_MENU, on_category("keyboard"), item_keyboard)
        menu.Bind(wx.EVT_MENU, on_category("moves"),    item_moves)
        menu.Bind(wx.EVT_MENU, on_category("clicks"),   item_clicks)
        menu.Bind(wx.EVT_MENU, on_category("scrolls"),  item_scrolls)
        menu.Bind(wx.EVT_MENU, on_category("keys"),     item_keys)
        menu.Bind(wx.EVT_MENU, on_category("combos"),   item_combos)
        menu.Bind(wx.EVT_MENU, on_session("start"),     item_session_start)
        menu.Bind(wx.EVT_MENU, on_session("stop"),      item_session_stop)
        menu.Bind(wx.EVT_MENU, self.OnToggleConsole,    item_console)
        menu.Bind(wx.EVT_MENU, self.OnClose,            item_exit)
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
        def make_size(geometry, w, h):
            scale = geometry.Width / float(w)
            return [int(geometry.X * scale), int(geometry.Y * scale), w, h]
        sizes = [make_size(d.Geometry, m.Width, m.Height)
                 for i in range(wx.Display.GetCount())
                 for d in [wx.Display(i)] for m in [d.GetCurrentMode()]]
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


    def OnSessionAction(self, action, event, session=None, category=None):
        arg = None

        if "open" == action:
            webbrowser.open(conf.WebUrl + "/sessions/%s" % session["id"])
            return
        elif "rename" == action:
            dlg = wx.TextEntryDialog(None, "Enter new name for session:", "Rename session",
                                     value=session["name"], style=wx.OK | wx.CANCEL)
            if self.icons: dlg.SetIcons(self.icons)
            dlg.CenterOnScreen()
            if wx.ID_OK != dlg.ShowModal(): return
            arg = dlg.GetValue().strip()
            if not arg or arg == session["name"]:
                return
        elif "clear" == action:
            arg = category
            label = ("%s events" % arg) if arg in conf.InputTables else arg or "all events"
            arg = arg or "all"

            if not session:
                choices = [format_session(x) for x in self.model.sessions]
                dlg = wx.SingleChoiceDialog(None, "Clear %s from:" % label, "Clear session", choices)
                if self.icons: dlg.SetIcons(self.icons)
                dlg.CenterOnScreen()
                res, sel = dlg.ShowModal(), dlg.GetSelection()
                dlg.Destroy()
                if wx.ID_OK != res: return
                session = self.model.sessions[sel]
            else:
                msg = 'Are you sure you want to clear %s from session "%s"?' % (label, session["name"])
                if wx.OK != wx.MessageBox(msg, conf.Title, wx.OK | wx.CANCEL | wx.ICON_WARNING): return
        elif "delete" == action:
            msg = 'Are you sure you want to delete session "%s"' % session["name"]
            res = YesNoCancelMessageBox(msg, conf.Title, wx.ICON_WARNING,
                                        yes="Delete", no="Clear events and delete")
            if wx.CANCEL == res: return
            if wx.NO == res:
                self.model.session_action("clear", session)
        elif "start" == action:
            arg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            dlg = wx.TextEntryDialog(None, "Enter name for new session:", "Start session",
                                     value=arg, style=wx.OK | wx.CANCEL)
            if self.icons: dlg.SetIcons(self.icons)
            dlg.CenterOnScreen()
            res, arg = dlg.ShowModal(), dlg.GetValue().strip()
            dlg.Destroy()
            if wx.ID_OK != res or not arg: return
        elif "stop" != action:
            return

        self.model.session_action(action, session, arg)


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


def YesNoCancelMessageBox(message, caption, icon=wx.ICON_NONE,
                          yes="&Yes", no="&No", cancel="Cancel"):
    """
    Opens a Yes/No/Cancel messagebox with custom labels, returns dialog result.

    @param   icon     dialog icon to use, one of wx.ICON_XYZ
    @param   default  default selected button, wx.YES or wx.NO
    """
    style = icon | wx.YES | wx.NO | wx.CANCEL
    dlg = wx.MessageDialog(None, message, caption, style)
    dlg.SetYesNoCancelLabels(yes, no, cancel)
    dlg.CenterOnScreen()
    res = dlg.ShowModal()
    dlg.Destroy()
    return res


def main():
    """Program entry point."""
    if conf.Frozen: multiprocessing.freeze_support()
    conf.init(), db.init(conf.DbPath, conf.DbStatements)
    try: db.execute("PRAGMA journal_mode = WAL")
    except Exception: pass

    if wx:
        name = re.sub(r"\W", "__", "-".join([conf.Title, conf.DbPath]))
        singlechecker = wx.SingleInstanceChecker(name)
        if singlechecker.IsAnotherRunning(): sys.exit()

        MainApp(redirect=True).MainLoop() # stdout/stderr directed to wx popup
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
    main()
