# -*- coding: utf-8 -*-
"""
Utilities.

------------------------------------------------------------------------------
This file is part of InputScope - mouse and keyboard input visualizer.
Released under the MIT License.

@author      Erki Suurjaak
@created     17.10.2021
@modified    10.04.2024
------------------------------------------------------------------------------
"""
import datetime
import errno
try: import fcntl
except ImportError: fcntl = None
import math
import os
try: import Queue as queue        # Py2
except ImportError: import queue  # Py3
import re
import stat
import sys
import threading
import time

try: import wx
except ImportError: wx = None


def format_bytes(size, precision=2, inter=" "):
    """Returns a formatted byte size (e.g. 421.45 MB)."""
    result = "0 bytes"
    if size:
        UNITS = [("bytes", "byte")[1 == size]] + [x + "B" for x in "KMGTPEZY"]
        exponent = min(int(math.log(size, 1024)), len(UNITS) - 1)
        result = "%.*f" % (precision, size / (1024. ** exponent))
        result += "" if precision > 0 else "."  # Do not strip integer zeroes
        result = result.rstrip("0").rstrip(".") + inter + UNITS[exponent]
    return result


def format_session(session, maxlen=20, quote=False, stamp=True):
    """Returns session name, ellipsized, with start datetime appended if different from name."""
    result = session["name"]
    if maxlen and len(result) > maxlen:
        result = result[:maxlen] + ".."
    if quote:
        result = '"%s"' % result
    dtstr = stamp and format_stamp(session["start"])
    return result if not stamp or dtstr == session["name"] else "%s (%s)" % (result, dtstr)


def format_stamp(stamp, fmt="%Y-%m-%d %H:%M"):
    """Formats UNIX timestamp or datetime object as datetime string."""
    try: number_types = (float, int, long)        # Py2
    except NameError: number_types = (float, int) # Py3
    dt = datetime.datetime.fromtimestamp(stamp) if isinstance(stamp, number_types) else stamp
    return dt.strftime(fmt)


def format_timedelta(timedelta):
    """Formats the timedelta as "3d 40h 23min 23sec"."""
    dd, rem = divmod(timedelta_seconds(timedelta), 24*3600)
    hh, rem = divmod(rem, 3600)
    mm, ss  = divmod(rem, 60)
    if mm or hh or dd: ss = int(ss)
    items = []
    for c, n in (dd, "d"), (hh, "h"), (mm, "min"), (ss, "sec"):
        f = "%d" % c if "sec" != n else str(round(c, 2)).rstrip("0").rstrip(".")
        if f != "0": items += [f + n]
    return " ".join(items or ["0 seconds"])


def format_weekday(value, long=False):
    """Formats datetime/date instance or string as weekday name."""
    if isinstance(value, str):
        value = datetime.datetime.strptime(value[:10], "%Y-%m-%d")
    return value.strftime("%A" if long else "%a")


def run_later(function, millis=0):
    """Runs the function in a later thread."""
    if wx: wx.CallLater(millis, function)
    else: threading.Thread(target=lambda: (time.sleep(millis / 1000.), function())).start()


def stamp_to_date(stamp):
    """Returns UNIX timestamp as datetime.date."""
    return datetime.datetime.fromtimestamp(stamp).date()


def timedelta_seconds(timedelta):
    """Returns the total timedelta duration in seconds."""
    if not isinstance(timedelta, datetime.timedelta):
        return timedelta
    return (timedelta.total_seconds() if hasattr(timedelta, "total_seconds")
            else timedelta.days * 24 * 3600 + timedelta.seconds +
                 timedelta.microseconds / 1000000.)


def zhex(v):
    """Returns number as zero-padded hex, e.g. "0x0C" for 12 and "0x0100" for 256."""
    if not v: return "0x00"
    sign, v = ("-" if v < 0 else ""), abs(v)
    return "%s0x%0*X" % (sign, 2 * int(1 + math.log(v) / math.log(2) // 8), v)


class LineQueue(threading.Thread):
    """Reads lines from a file-like object and pushes to self.queue."""
    def __init__(self, input):
        threading.Thread.__init__(self)
        self.daemon = True
        self.input, self.queue = input, queue.Queue()
        self.start()

    def run(self):
        for line in iter(self.input.readline, ""):
            try: line = line.decode("utf-8") # Py2
            except Exception: pass
            self.queue.put(line.strip())


class QueueLine(object):
    """Queue-like interface for writing lines to a file-like object."""
    def __init__(self, output): self.output = output
    def put(self, item):
        try:
            if "b" in getattr(self.output, "mode", ""): # Py2
                try: item = item.encode("utf-8")
                except Exception: pass
            self.output.write("%s\n" % item)
            self.output.flush()
        except IOError as e:
            if e.errno != errno.EINVAL: raise # Invalid argument, probably stale pipe


class SingleInstanceChecker(object):
    """
    Allows checking that only a single instance of a program is running, per user login.

    Uses wx.SingleInstanceChecker in Windows, and a custom lockfile otherwise,
    as wx.SingleInstanceChecker in Linux can fail.
    """

    def __init__(self, name=None, path=None, appname=None):
        """
        Creates new SingleInstanceChecker, acquiring exclusive lock on name.

        @param   name     unique ID for application, by default constructed from app name + username;
                          best if contains alphanumerics and other basic printables only
        @param   path     directory of lockfile, ignored in Windows, defaults to user data folder
        @param   appname  used for lockfile subdirectory under path if present, ignored in Windows
        """
        self._name     = name.strip() if name else None
        self._lockdir  = path
        self._appname  = appname.strip() if appname else None
        self._checker  = None # wx.SingleInstanceChecker instance in Windows if wx available
        self._lockpath = None # Path for lockfile in non-Windows
        self._lockfd   = None # File descriptor for lockfile
        self._hasother = None # True: another is running, False: only this running, None: unknown
        self._otherpid = None # Process ID of the other detected instance
        if "win32" != sys.platform: self._PopulatePath(), self._Lock()
        else: self._checker = wx.SingleInstanceChecker(*[name] if name else [])


    def IsAnotherRunning(self):
        """Returns whether another copy of this program is already running, or None if unknown."""
        if self._checker is not None: return self._checker.IsAnotherRunning()
        if self._hasother: self._Lock() # Try locking again, maybe the other has exited
        else: # Check if lockfile handle is still valid
            try: deleted = not os.fstat(self._lockfd).st_nlink # Number of hard links
            except Exception: deleted = None
            if deleted:
                try: os.close(self._lockfd)
                except Exception: pass
                self._lockfd = None
                self._Lock()
        return self._hasother


    def GetOtherPid(self):
        """Returns the process ID of the other running instance, or None if unknown or Windows."""
        return self._otherpid


    def __del__(self):
        """Unlocks current lock, if any."""
        if self._checker is not None: del self._checker
        else: self._Unlock()
        self._checker = None


    def _PopulatePath(self):
        """Populates lockfile path."""
        name = self._name
        if not name:
            name = os.getenv("USER", os.getenv("USERNAME"))
            procname = sys.executable or (sys.argv[0] if sys.argv else "")
            name = re.sub(r"\W", "__", "__".join(filter(bool, (procname, name)))) or "__"
        lockdir = self._lockdir or os.path.join(os.path.expanduser("~"), ".local", "share")
        if self._appname: lockdir = os.path.join(lockdir, self._appname.lower())
        self._lockpath = os.path.join(lockdir, "%s.lock" % name)


    def _Lock(self):
        """Tries to create lockfile and acquire lock, sets instance status."""
        if self._lockfd or not fcntl: return

        self._hasother = self._otherpid = None
        try:
            try: os.makedirs(os.path.dirname(self._lockpath))
            except Exception: pass

            flags, mode = os.O_RDWR | os.O_CREAT, stat.S_IRUSR | stat.S_IWUSR
            umask0 = os.umask(0) # Override default umask
            try: self._lockfd = os.open(self._lockpath, flags, mode)
            finally: os.umask(umask0) # Restore default umask

            try: fcntl.lockf(self._lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB) # Exclusive non-blocking
            except (IOError, OSError):
                try: self._otherpid = int(os.read(self._lockfd, 1024))
                except Exception: pass
                try: os.close(self._lockfd)
                except Exception: pass
                self._hasother, self._lockfd = True, None
            else:
                self._hasother = False
                try: os.write(self._lockfd, b"%d" % os.getpid()), os.fsync(self._lockfd)
                except Exception: pass
        except Exception:
            try: os.close(self._lockfd)
            except Exception: pass
            self._lockfd = None


    def _Unlock(self):
        """Unlocks and closes and deletes lockfile, if any."""
        if not self._lockfd: return
        funcs  = (fcntl.lockf,                   os.close,       os.unlink)
        argses = ([self._lockfd, fcntl.LOCK_UN], [self._lockfd], [self._lockpath])
        for func, args in zip(funcs, argses):
            try: func(*args)
            except Exception: pass
        self._lockfd = None
