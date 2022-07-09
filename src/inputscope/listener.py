# -*- coding: utf-8 -*-
"""
Mouse and keyboard listener, logs events to database.

--quiet      prints out nothing


Commands from stdin:

start          CATEGORY
stop           CATEGORY
clear          CATEGORY ?DATE1 ?DATE2
screen_size    [DISPLAY0 x, y, w, h], ..

session start  NAME
session stop
session rename NAME2 ID
session clear  CATEGORY ID
session delete ID


@author      Erki Suurjaak
@created     06.04.2015
@modified    09.07.2022
"""
from __future__ import print_function
from collections import defaultdict
import datetime
try: import Queue as queue        # Py2
except ImportError: import queue  # Py3
import sys
import threading
import time
import traceback

import pynput

from . import conf
from . import db
from . util import LineQueue, stamp_to_date, zhex

DEBUG = False


class Listener(threading.Thread):
    """Runs mouse and keyboard listeners, and handles incoming commands."""

    def __init__(self, inqueue, outqueue=None):
        threading.Thread.__init__(self)
        self.inqueue = inqueue
        self.running = False
        self.mouse_handler = None
        self.key_handler   = None
        self.data_handler = DataHandler(getattr(outqueue, "put", lambda x: x))

    def run(self):
        self.running = True
        while self.running:
            command = self.inqueue.get()
            if not command or not self.running: continue # while self.running
            try: self.handle_command(command)
            except Exception:
                print("Error handling command %r" % command)
                traceback.print_exc()

    def handle_command(self, command):
        if command.startswith("start ") or command.startswith("stop "):
            action, category = command.split()
            if category not in conf.InputFlags: return

            # Event input (mouse|keyboard), None if category itself is input
            input = next((k for k, vv in conf.InputEvents.items() if category in vv), None)
            attr = conf.InputFlags[category]
            on = ("start" == action)
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

            if bool(conf.MouseEnabled) != bool(self.mouse_handler):
                if self.mouse_handler: self.mouse_handler = self.mouse_handler.stop()
                else: self.mouse_handler = MouseHandler(self.data_handler.handle)
            if bool(conf.KeyboardEnabled) != bool(self.key_handler):
                if self.key_handler: self.key_handler = self.key_handler.stop()
                else: self.key_handler = KeyHandler(self.data_handler.handle)
        elif command.startswith("clear "):
            parts = command.split()[1:]
            category, dates = parts[0], parts[1:]
            if "all" == category: tables = sum(conf.InputEvents.values(), ())
            elif category in conf.InputEvents: tables = conf.InputEvents[category]
            else: tables = [category]
            where = [("day", (">=", dates[0])), ("day", ("<=", dates[1]))] if dates else []
            count_deleted = 0
            for table in tables:
                count_deleted += db.delete(table, where=where)
                db.delete("counts", where=where, type=table)
            if count_deleted:
                where = [("day1", (">=", dates[0])), ("day2", ("<=", dates[1]))] if dates else []
                for session in db.fetch("sessions", where=where):
                    retain = False
                    where = [("stamp", (">=", session["start"])), ("stamp", ("<", session["end"]))]
                    for table in tables:
                        retain = retain or db.fetchone(table, "1", where=where)
                    if not retain:
                        db.delete("sessions", id=session["id"])
        elif command.startswith("screen_size "):
            # "screen_size [0, 0, 1920, 1200] [1920, 0, 1000, 800]"
            sizestrs = list(filter(bool, (x.strip() for x in command[12:].replace("[", "").split("]"))))
            sizes = sorted([[int(x) for x in s.replace(",", "").split()] for s in sizestrs])
            for i, size in enumerate(sizes):
                db.insert("screen_sizes", x=size[0], y=size[1], w=size[2], h=size[3], display=i)
            self.data_handler.screen_sizes = sizes
        elif command.startswith("session "):
            parts = command.split()[1:]
            action, args = parts[0], parts[1:]
            if "start" == action and args:
                stamp, day = next((x, stamp_to_date(x)) for x in [time.time()])
                db.update("sessions", {"day2": day, "end": stamp}, end=None)
                db.insert("sessions", name=" ".join(args), start=stamp, day1=day)
            elif "stop" == action:
                stamp, day = next((x, stamp_to_date(x)) for x in [time.time()])
                db.update("sessions", {"day2": day, "end": time.time()}, end=None)
            elif "rename" == action and len(args) > 1:
                name2, sid = " ".join(args[:-1]), args[-1]
                db.update("sessions", {"name": name2}, id=sid)
            elif "clear" == action and len(args) == 2:
                category, sess = args[0], db.fetchone("sessions", id=args[1])
                if "all" == category: tables = sum(conf.InputEvents.values(), ())
                elif category in conf.InputEvents: tables = conf.InputEvents[category]
                else: tables = [category]
                day1 = stamp_to_date(sess["start"])
                day2 = stamp_to_date(sess["end"] or time.time())
                step = datetime.timedelta(days=1)
                days = [day1 + i * step for i in range(abs((day2 - day1).days + 1))]
                where = [("stamp", (">=", sess["start"]))]
                if sess["end"]: where += [("stamp", ("<", sess["end"]))]

                for table, day in ((t, d) for t in tables for d in days):
                    count = db.delete(table, [("day", day)] + where)
                    db.update("counts", {"count": ("EXPR", "count - %s" % count)}, day=day, type=table)
            elif "delete" == action and args:
                db.delete("sessions", id=args[0])
        elif "vacuum" == command:
            db.execute("VACUUM")
        elif "exit" == command:
            self.stop()

    def stop(self):
        self.running = False
        self.mouse_handler and self.mouse_handler.stop()
        self.key_handler and self.key_handler.stop()
        self.data_handler.stop()
        self.inqueue.put(None) # Wake up thread waiting on queue
        db.close()
        sys.exit()



class DataHandler(threading.Thread):
    """Output thread, inserts events to database and to output function."""

    def __init__(self, output):
        threading.Thread.__init__(self)
        self.counts = defaultdict(int) # {type: count}
        self.output = output
        self.inqueue = queue.Queue()
        self.screen_sizes = [[0, 0] + list(conf.DefaultScreenSize)]
        self.running = False
        self.start()

    def run(self):
        self.running = True
        dbqueue = [] # Data queued for later after first insert failed
        db.insert("app_events", type="start")

        def get_display(pt):
            """Returns (display index, [x, y, w, h]) for mouse event position."""
            for i, size in enumerate(self.screen_sizes):
                # Point falls exactly into display
                if  size[0] <= pt[0] <= size[0] + size[2] \
                and size[1] <= pt[1] <= size[1] + size[3]:
                    return i, size
            if pt[0] >= self.screen_sizes[-1][0] + self.screen_sizes[-1][2] \
            or pt[1] >= self.screen_sizes[-1][1] + self.screen_sizes[-1][3]:
                # Point is beyond the last display
                return len(self.screen_sizes) - 1, self.screen_sizes[-1]
            for i, size in enumerate(self.screen_sizes):
                # One coordinate falls into display, other is off screen
                if size[0] <= pt[0] <= size[0] + size[2] \
                or size[1] <= pt[1] <= size[1] + size[3]:
                    return i, size
            return 0, self.screen_sizes[0] # Fall back to first display

        def rescale(pt):
            """Remaps point to heatmap size for less granularity."""
            HS = conf.MouseHeatmapSize
            _, screen_size = get_display(pt)
            SC = [screen_size[i + 2] / float(HS[i]) for i in (0, 1)]
            return [min(int(pt[i] / SC[i]), HS[i]) for i in (0, 1)]

        def one_line(pt1, pt2, pt3):
            """Returns whether points more or less fall onto one line."""
            (x1, y1), (x2, y2), (x3, y3) = list(map(rescale, (pt1, pt2, pt3)))
            if  not (x1 >= x2 >= x3) and not (y1 >= y2 >= y3) \
            and not (x1 <= x2 <= x3) and not (y1 <= y2 <= y3): return False
            return abs((y1 - y2) * (x1 - x3) - (y1 - y3) * (x1 - x2)) <= conf.MouseMoveJoinRadius

        def sign(v): return -1 if v < 0 else 1 if v > 0 else 0

        stamps0, stamps1 = defaultdict(float), defaultdict(float) # {category: stamp}
        lasts = {"moves": None, "keys": None, "combos": None} # {event category: [values]}
        while self.running:
            data, items = self.inqueue.get(), []
            while data:
                items.append(data)
                try: data = self.inqueue.get(block=False)
                except queue.Empty: data = None
            if not items or not self.running: continue # while self.running

            move0, move1, scroll0 = None, None, None # For merging events in this iteration
            for data in items:
                category = data.pop("type")
                if category in conf.InputEvents["mouse"]:
                    data["display"], _ = get_display([data["x"], data["y"]])
                stamps0.update(stamps1)
                stamps1[category] = data["stamp"]

                if category in lasts:
                    if category in conf.InputEvents["mouse"]: # Skip if same downscaled pos as last
                        INTERVAL = conf.MouseMoveJoinInterval
                        newlast = [data["display"]] + rescale([data["x"], data["y"]])
                    else: # Skip if key appears held down (same value repeating rapidly)
                        INTERVAL = conf.KeyboardJoinInterval
                        newlast = [data["key"], data["realkey"]]
                    if INTERVAL and lasts[category] == newlast \
                    and data["stamp"] - stamps0[category] < INTERVAL:
                        if "moves" == category: move0, move1 = move1, data
                        continue # for data
                    lasts[category] = newlast

                if "moves" == category: # Reduce mouse move events
                    if conf.MouseMoveJoinInterval and move0 and move1 \
                    and move1["stamp"] - move0["stamp"] < conf.MouseMoveJoinInterval \
                    and data["stamp"]  - move1["stamp"] < conf.MouseMoveJoinInterval \
                    and move0["display"] == move1["display"] == data["display"] \
                    and one_line(*[(v["x"], v["y"]) for v in (move0, move1, data)]):
                        move1.update(data)
                        continue # for data
                    move0, move1 = move1, data
                elif "scrolls" == category: # Reduce mouse scroll events
                    if scroll0 and conf.MouseScrollJoinInterval \
                    and scroll0["display"] == data["display"] \
                    and sign(scroll0["dx"]) == sign(data["dx"]) \
                    and sign(scroll0["dy"]) == sign(data["dy"]) \
                    and data["stamp"] - stamps0[category] < conf.MouseScrollJoinInterval:
                        for k in ("dx", "dy"): scroll0[k] += data[k]
                        for k in ( "x",  "y"): scroll0[k]  = data[k]
                        continue # for data
                    scroll0 = data

                self.counts[category] += 1
                dbqueue.append((category, data))

            try:
                while dbqueue: db.insert(*dbqueue.pop(0))
            except Exception as e: print(e)
            self.output(dict(self.counts))
            if conf.EventsWriteInterval > 0: time.sleep(conf.EventsWriteInterval)

    def stop(self):
        self.running = False
        self.inqueue.put(None) # Wake up thread waiting on queue
        db.close()

    def handle(self, **kwargs):
        category = kwargs.get("type")
        if not getattr(conf, conf.InputFlags.get(category), False): return
        kwargs.update(day=datetime.date.today(), stamp=time.time())
        if self.inqueue.qsize() < conf.MaxEventsForQueue: self.inqueue.put(kwargs)



class MouseHandler(object):
    """Listens to mouse events and forwards to output."""

    def __init__(self, output):
        self._output = output
        self._buttons = {"left": 1, "right": 2, "middle": 3, "unknown": 0}
        for b in pynput.mouse.Button:
            if b.name not in self._buttons:
                self._buttons[b.name] = len(self._buttons)
        self._listener = pynput.mouse.Listener(
            on_move=self.move, on_click=self.click, on_scroll=self.scroll
        )
        self._listener.start()

    def click(self, x, y, button, pressed, *a, **kw):
        if pressed:
            buttonindex = self._buttons.get(button.name, 0)
            self._output(type="clicks", x=x, y=y, button=buttonindex)

    def move(self, x, y, *a, **kw):
        self._output(type="moves", x=x, y=y)

    def scroll(self, x, y, dx, dy, *a, **kw):
        self._output(type="scrolls", x=x, y=y, dx=dx, dy=dy)

    def stop(self): self._listener.stop()
        


class KeyHandler(object):
    """Listens to keyboard events and forwards to output."""
    CONTROLCODES = {"\x00": "Nul", "\x01": "Start-Of-Header", "\x02": "Start-Of-Text", "\x03": "Break", "\x04": "End-Of-Transmission", "\x05": "Enquiry", "\x06": "Ack", "\x07": "Bell", "\x08": "Backspace", "\x09": "Tab", "\x0a": "Linefeed", "\x0b": "Vertical-Tab", "\x0c": "Form-Fe", "\x0d": "Enter", "\x0e": "Shift-In", "\x0f": "Shift-Out", "\x10": "Data-Link-Escape", "\x11": "Devicecontrol1", "\x12": "Devicecontrol2", "\x13": "Devicecontrol3", "\x14": "Devicecontrol4", "\x15": "Nak", "\x16": "Syn", "\x17": "End-Of-Transmission-Block", "\x18": "Break", "\x19": "End-Of-Medium", "\x1a": "Substitute", "\x1b": "Escape", "\x1c": "File-Separator", "\x1d": "Group-Separator", "\x1e": "Record-Separator", "\x1f": "Unit-Separator", "\x20": "Space", "\x7f": "Del", "\xa0": "Non-Breaking Space"}
    NUMPAD_SPECIALS = [("Insert", False), ("Delete", False), ("Home", False), ("End", False), ("PageUp", False), ("PageDown", False), ("Up", False), ("Down", False), ("Left", False), ("Right", False), ("Clear", False), ("Enter", True)]
    NUMPAD_CHARS = {"0": "Numpad0", "1": "Numpad1", "2": "Numpad2", "3": "Numpad3", "4": "Numpad4", "5": "Numpad5", "6": "Numpad6", "7": "Numpad7", "8": "Numpad8", "9": "Numpad9", "/": "Numpad-Divide", "*": "Numpad-Multiply", "-": "Numpad-Subtract", "+": "Numpad-Add", }
    MODIFIERNAMES = {"Lcontrol": "Ctrl", "Rcontrol": "Ctrl", "Lshift": "Shift", "Rshift": "Shift", "Alt": "Alt", "Lwin": "Win", "Rwin": "Win", "AltGr": "AltGr"}
    RENAMES = {"Prior": "PageUp", "Next": "PageDown", "Lmenu": "Alt", "Rmenu": "AltGr", "Apps": "Menu", "Return": "Enter", "Back": "Backspace", "Capital": "CapsLock", "Numlock": "NumLock", "Snapshot": "PrintScreen", "Scroll": "ScrollLock", "Decimal": "Numpad-Decimal", "Divide": "Numpad-Divide", "Subtract": "Numpad-Subtract", "Multiply": "Numpad-Multiply", "Add": "Numpad-Add", "Cancel": "Break", "Control_L": "Lcontrol", "Control_R": "Rcontrol", "Alt_L": "Alt", "Shift_L": "Lshift", "Shift_R": "Rshift", "Super_L": "Lwin", "Super_R": "Rwin", "BackSpace": "Backspace", "L1": "F11", "L2": "F12", "Page_Up": "PageUp", "Print": "PrintScreen", "Scroll_Lock": "ScrollLock", "Caps_Lock": "CapsLock", "Num_Lock": "NumLock", "Begin": "Clear", "Super": "Win", "Mode_switch": "AltGr"}
    STICKY_KEYS = ["Lcontrol", "Rcontrol", "Lshift", "Rshift", "Alt", "AltGr", "Lwin", "Rwin", "ScrollLock", "CapsLock", "NumLock"]
    PYNPUT_NAMES = {"alt_l": "Alt", "alt_r": "AltGr", "cmd": "Lwin", "cmd_l": "Lwin", "cmd_r": "Rwin", "ctrl": "Lcontrol", "ctrl_l": "Lcontrol", "ctrl_r": "Rcontrol", "esc": "Escape", "shift": "Lshift", "shift_l": "Lshift", "shift_r": "Rshift", "pause": "Break"}
    VK_NAMES = { # Virtual keycode values on Windows
        226: "Oem_102",    # Right from Lshift
        188: "Oem_Comma",  # Right from M
        190: "Oem_Period", # Right from Oem_Comma
        221: "Oem_6",      # Left from Rshift

        186: "Oem_1",      # Right from L
        191: "Oem_2",      # Right from Oem_1
        220: "Oem_5",      # Right from Oem_2

        192: "Oem_3",      # Right from P
        219: "Oem_4",      # Right from Oem_3

        222: "Oem_7",      # Left  from 1
        189: "Oem_Minus",  # Right from 0
        187: "Oem_Plus",   # Left  from Backspace

         96: "Numpad0",
         97: "Numpad1",
         98: "Numpad2",
         99: "Numpad3",
        100: "Numpad4",
        101: "Numpad5",
        102: "Numpad6",
        103: "Numpad7",
        104: "Numpad8",
        105: "Numpad9",

         12: "Numpad-Clear", # Numpad5 without NumLock
        106: "Numpad-Multiply",
        107: "Numpad-Add",
        109: "Numpad-Subtract",
        110: "Numpad-Delete",
        111: "Numpad-Divide",

         21: "IME Hangul/Kana",
         23: "IME Junja",
         24: "IME final",
         25: "IME Hanja/Kanji",

        172: "Web/Home", # Extra top keys
        173: "Volume Mute",
        174: "Volume Down",
        175: "Volume Up",
        176: "Media Next",
        177: "Media Prev",
        178: "Media Stop",
        179: "Media Play/Pause",
        180: "Email",
        181: "Media Select",
        182: "Application 1",
        183: "Application 2",
    }
    OTHER_VK_NAMES = { # Not Windows
        65027:     "AltGr",
        65437:     "Numpad-Clear", # Numpad5 without NumLock
        269025041: "MediaVolumeDown",
        269025042: "MediaVolumeMute",
        269025043: "MediaVolumeUp",
        269025044: "MediaPlayPause",
        269025048: "Web/Home",
        269025049: "Email",
        269025053: "Calculator",
        269025074: "Media",
    }


    def __init__(self, output):
        self.KEYNAMES = self.PYNPUT_NAMES.copy() # pynput.Key.xyz.name: label
        for key in pynput.keyboard.Key:
            if key.name not in self.KEYNAMES:
                self.KEYNAMES[key.name] = self.nicename(key.name)

        self._output = output
        self._downs  = {} # {key name: bool}
        self._modifiers     = dict((x, False) for x in self.MODIFIERNAMES.values())
        self._realmodifiers = dict((x, False) for x in self.MODIFIERNAMES)
        # Extended keys: AltGr, Rcontrol; clustered Insert/Delete/navigation and arrows;
        # NumLock; Break; PrintScreen; Numpad-Divide, Numpad-Enter
        self._is_extended = None # Current key is extended key

        args = dict(on_press=  lambda k, *a, **kw: self.on_event(True,  k),
                    on_release=lambda k, *a, **kw: self.on_event(False, k))
        if "win32" == sys.platform:
            args.update(win32_event_filter=self.win32_filter)
        # Cannot inherit from pynput.keyboard.Listener directly,
        # as it does hacky magic dependant on self.__class__.__module__
        self._listener  = pynput.keyboard.Listener(**args)
        self._listener.start()


    def on_event(self, pressed, key):
        """Handler for key event."""
        mykey, realkey = self.extract(key)
        if not mykey and not realkey: return

        if realkey in self.MODIFIERNAMES:
            self._modifiers[self.MODIFIERNAMES[realkey]] = pressed
            self._realmodifiers[realkey] = pressed

        if realkey in self.STICKY_KEYS and self._downs.get(realkey) == pressed:
            return # Avoid multiple events on holding down Shift etc
        self._downs[realkey] = pressed
        if not conf.KeyboardEnabled or not pressed: return

        if DEBUG: print("Adding key %r (real %r)" % (mykey, realkey))
        self._output(type="keys", key=mykey, realkey=realkey)

        if mykey not in self.MODIFIERNAMES and conf.KeyboardCombosEnabled:
            modifier = "-".join(k for k in ["Ctrl", "Alt", "AltGr", "Shift", "Win"]
                                if self._modifiers[k])
            if modifier and modifier != "Shift": # Shift-X is not a combo
                mykey = "%s-%s" % (modifier, realkey)
                realmodifier = "-".join(k for k, v in self._realmodifiers.items() if v)
                realkey = "%s-%s" % (realmodifier, realkey)
                if DEBUG: print("Adding combo %r (real %r)" % (mykey, realkey))
                self._output(type="combos", key=mykey, realkey=realkey)


    def extract(self, key):
        """Returns (key name or uppercase char, realkey name) for pynput event."""
        if isinstance(key, pynput.keyboard.Key):
            name, char, vk = key.name, key.value.char, key.value.vk
        else: # pynput.keyboard.KeyCode
            name, char, vk = None, key.char, key.vk

        if name:
            name = self.KEYNAMES.get(name) or self.nicename(name)
            name = realname = self.RENAMES.get(name, name)
            if vk and (name, self._is_extended) in self.NUMPAD_SPECIALS:
                name = realname = "Numpad-" + name
        elif ord("A") <= vk <= ord("Z") or ord("0") <= vk <= ord("9"):
            # Common A..Z 0..9 keys, whatever the chars
            name, realname = char.upper() if char else chr(vk), chr(vk)

        if not name and "win32" != sys.platform:
            if   char and vk:               name = char.upper()
            elif char in self.NUMPAD_CHARS: name = self.NUMPAD_CHARS[char]
            elif vk in self.OTHER_VK_NAMES: name = self.OTHER_VK_NAMES[vk]
            else: name = char.upper() if char else zhex(vk) if vk else None
            realname = name
        elif vk in self.VK_NAMES: # Numpad and extra keys
            realname = self.VK_NAMES[vk]
            name = char.upper() if char and "Oem_" in realname else realname
        elif name: pass
        elif char and vk:
            name = char.upper()
            realname = chr(vk) if ord("0") <= vk <= ord("9") else zhex(vk)
        else: realname = None

        if name in self.CONTROLCODES:
            realname = self.CONTROLCODES.get(realname, realname)
            # Combos can also produce control codes, e.g. Ctrl-Y: End-of-Medium
            if self._modifiers["Ctrl"]: name = realname
            else: name = self.CONTROLCODES[name]

        if vk in conf.CustomKeys:
            name = realname = conf.CustomKeys[vk]

        return name, realname


    def win32_filter(self, msg, data):
        """Stores extended-key bit for upcoming press/release event."""
        # Pressing AltGr generates a dummy Lcontrol event: skip on_event()
        if 541 == data.scanCode and 162 == data.vkCode: return False
        # KBDLLHOOKSTRUCT.flags bit 0 is LLKHF_EXTENDED
        self._is_extended = data.flags & 0x01


    def nicename(self, s):
        """Transforms snake case like "alt_gr" to Pascal case like "AltGr"."""
        return "".join(x.capitalize() for x in s.split("_"))


    def stop(self): self._listener.stop()



def start(inqueue, outqueue=None):
    """Starts the listener with incoming and outgoing queues."""
    conf.init(), db.init(conf.DbPath, conf.DbStatements)

    # Carry out db update for tables lacking expected new columns
    for (table, col), sqls in conf.DbUpdateStatements:
        if not any(col == x["name"] for x in db.execute("PRAGMA table_info(%s)" % table)):
            for sql in sqls: db.execute(sql)

    try: db.execute("PRAGMA journal_mode = WAL")
    except Exception: pass

    listener = Listener(inqueue, outqueue)
    try: listener.run()
    except KeyboardInterrupt: listener.stop()


def main():
    """Entry point for stand-alone execution."""
    conf.init()
    inqueue = LineQueue(sys.stdin).queue
    outqueue = type("", (), {"put": lambda self, x: print("\r%s" % x, end=" ")})()
    if "--quiet" in sys.argv: outqueue = None
    if conf.MouseEnabled:    inqueue.put("start mouse")
    if conf.KeyboardEnabled: inqueue.put("start keyboard")
    start(inqueue, outqueue)


if "__main__" == __name__:
    main()
