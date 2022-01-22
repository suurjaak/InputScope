# -*- coding: utf-8 -*-
"""
Utilities.

@author      Erki Suurjaak
@created     17.10.2021
@modified    18.10.2021
"""
import datetime
import errno
import math
try: import Queue as queue        # Py2
except ImportError: import queue  # Py3
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
    """Formats the timedelta as "3d 40h 23min 23.1sec"."""
    dd, rem = divmod(timedelta_seconds(timedelta), 24*3600)
    hh, rem = divmod(rem, 3600)
    mm, ss  = divmod(rem, 60)
    items = []
    for c, n in (dd, "d"), (hh, "h"), (mm, "min"), (ss, "sec"):
        f = "%d" % c if "sec" != n else str(round(c, 2)).rstrip("0").rstrip(".")
        if f != "0": items += [f + n]
    return " ".join(items or ["0 seconds"])


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
