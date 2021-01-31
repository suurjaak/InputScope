# -*- coding: utf-8 -*-
"""
Mouse and keyboard listener, logs events to database.

--quiet      prints out nothing

@author      Erki Suurjaak
@created     06.04.2015
@modified    31.01.2021
"""
from __future__ import print_function
import datetime
import Queue
import sys
import threading
import time
import traceback
import pykeyboard
import pymouse

import conf
import db

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
            for table in tables:
                db.delete("counts", where=where, type=table)
                db.delete(table, where=where)
        elif command.startswith("screen_size "):
            # "screen_size [0, 0, 1920, 1200] [1920, 0, 1000, 800]"
            sizestrs = filter(bool, map(str.strip, command[12:].replace("[", "").split("]")))
            sizes = sorted(map(int, s.replace(",", "").split()) for s in sizestrs)
            for i, size in enumerate(sizes):
                db.insert("screen_sizes", x=size[0], y=size[1], w=size[2], h=size[3], display=i)
            self.data_handler.screen_sizes = sizes
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
        self.counts = {} # {type: count}
        self.output = output
        self.inqueue = Queue.Queue()
        self.lasts = {"moves": None}
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
                and size[1] <= pt[1] <= size[1] + size[3]: return i, size
            if pt[0] >= self.screen_sizes[-1][0] + self.screen_sizes[-1][2] \
            or pt[1] >= self.screen_sizes[-1][1] + self.screen_sizes[-1][3]:
                # Point is beyond the last display
                return len(self.screen_sizes) - 1, self.screen_sizes[-1]
            for i, size in enumerate(self.screen_sizes):
                # One coordinate falls into display, other is off screen
                if size[0] <= pt[0] <= size[0] + size[2] \
                or size[1] <= pt[1] <= size[1] + size[3]: return i, size
            return 0, self.screen_sizes[0] # Fall back to first display

        def rescale(pt):
            """Remaps point to heatmap size for less granularity."""
            HS = conf.MouseHeatmapSize
            _, screen_size = get_display(pt)
            SC = [screen_size[i + 2] / float(HS[i]) for i in (0, 1)]
            return [min(int(pt[i] / SC[i]), HS[i]) for i in (0, 1)]

        def one_line(pt1, pt2, pt3):
            """Returns whether points more or less fall onto one line."""
            (x1, y1), (x2, y2), (x3, y3) = map(rescale, (pt1, pt2, pt3))
            if  not (x1 >= x2 >= x3) and not (y1 >= y2 >= y3) \
            and not (x1 <= x2 <= x3) and not (y1 <= y2 <= y3): return False
            return abs((y1 - y2) * (x1 - x3) - (y1 - y3) * (x1 - x2)) <= conf.MouseMoveJoinRadius

        while self.running:
            data, items = self.inqueue.get(), []
            while data:
                items.append(data)
                try: data = self.inqueue.get(block=False)
                except Queue.Empty: data = None
            if not items or not self.running: continue # while self.running

            move0, move1 = None, None
            for data in items:
                category = data.pop("type")
                if category in conf.InputEvents["mouse"]:
                    data["display"], _ = get_display([data["x"], data["y"]])
                if category in self.lasts: # Skip event if same position as last
                    pos = rescale([data["x"], data["y"]])
                    if self.lasts[category] == pos: continue # for data
                    self.lasts[category] = pos

                if "moves" == category:
                    if move0 and move1 and move1["stamp"] - move0["stamp"] < conf.MouseMoveJoinInterval \
                    and data["stamp"] - move1["stamp"] < conf.MouseMoveJoinInterval \
                    and move0["display"] == move1["display"] == data["display"]:
                        if one_line(*[(v["x"], v["y"]) for v in (move0, move1, data)]):
                            move1.update(data) # Reduce move events
                            continue # for data
                    move0, move1 = move1, data

                if category not in self.counts: self.counts[category] = 0
                self.counts[category] += 1
                dbqueue.append((category, data))

            try:
                while dbqueue:
                    db.insert(*dbqueue[0])
                    dbqueue.pop(0)
            except StandardError as e:
                print(e, category, data)
            self.output(self.counts)
            if conf.EventsWriteInterval > 0: time.sleep(conf.EventsWriteInterval)

    def stop(self):
        self.running = False
        self.inqueue.put(None) # Wake up thread waiting on queue
        db.close()

    def handle(self, **kwargs):
        category = kwargs.get("type")
        if not getattr(conf, conf.InputFlags.get(category), False): return
        kwargs.update(day=datetime.date.today(), stamp=time.time())
        self.inqueue.put(kwargs)



class MouseHandler(pymouse.PyMouseEvent):
    """Listens to mouse events and forwards to output."""

    def __init__(self, output):
        pymouse.PyMouseEvent.__init__(self)
        self._output = output
        self.start()

    def click(self, x, y, button, press, *a, **kw):
        if press: self._output(type="clicks", x=x, y=y, button=button)

    def move(self, x, y, *a, **kw):
        self._output(type="moves", x=x, y=y)

    def scroll(self, x, y, wheel, *a, **kw):
        self._output(type="scrolls", x=x, y=y, wheel=wheel)



class KeyHandler(pykeyboard.PyKeyboardEvent):
    """Listens to keyboard events and forwards to output."""
    CONTROLCODES = {"\x00": "Nul", "\x01": "Start-Of-Header", "\x02": "Start-Of-Text", "\x03": "Break", "\x04": "End-Of-Transmission", "\x05": "Enquiry", "\x06": "Ack", "\x07": "Bell", "\x08": "Backspace", "\x09": "Tab", "\x0a": "Linefeed", "\x0b": "Vertical-Tab", "\x0c": "Form-Fe", "\x0d": "Enter", "\x0e": "Shift-In", "\x0f": "Shift-Out", "\x10": "Data-Link-Escape", "\x11": "Devicecontrol1", "\x12": "Devicecontrol2", "\x13": "Devicecontrol3", "\x14": "Devicecontrol4", "\x15": "Nak", "\x16": "Syn", "\x17": "End-Of-Transmission-Block", "\x18": "Break", "\x19": "End-Of-Medium", "\x1a": "Substitute", "\x1b": "Escape", "\x1c": "File-Separator", "\x1d": "Group-Separator", "\x1e": "Record-Separator", "\x1f": "Unit-Separator", "\x20": "Space", "\x7f": "Del", "\xa0": "Non-Breaking Space"}
    NUMPAD_SPECIALS = [("Insert", False), ("Delete", False), ("Home", False), ("End", False), ("PageUp", False), ("PageDown", False), ("Up", False), ("Down", False), ("Left", False), ("Right", False), ("Clear", False), ("Enter", True)]
    MODIFIERNAMES = {"Lcontrol": "Ctrl", "Rcontrol": "Ctrl", "Lshift": "Shift", "Rshift": "Shift", "Alt": "Alt", "AltGr": "Alt", "Lwin": "Win", "Rwin": "Win"}
    RENAMES = {"Prior": "PageUp", "Next": "PageDown", "Lmenu": "Alt", "Rmenu": "AltGr", "Apps": "Menu", "Return": "Enter", "Back": "Backspace", "Capital": "CapsLock", "Numlock": "NumLock", "Snapshot": "PrintScreen", "Scroll": "ScrollLock", "Decimal": "Numpad-Decimal", "Divide": "Numpad-Divide", "Subtract": "Numpad-Subtract", "Multiply": "Numpad-Multiply", "Add": "Numpad-Add", "Cancel": "Break", "Control_L": "Lcontrol", "Control_R": "Rcontrol", "Alt_L": "Alt", "Shift_L": "Lshift", "Shift_R": "Rshift", "Super_L": "Lwin", "Super_R": "Rwin", "BackSpace": "Backspace", "L1": "F11", "L2": "F12", "Page_Up": "PageUp", "Print": "PrintScreen", "Scroll_Lock": "ScrollLock", "Caps_Lock": "CapsLock", "Num_Lock": "NumLock", "Begin": "Clear", "Super": "Win", "Mode_switch": "AltGr"}
    KEYS_DOWN = (0x0100, 0x0104) # [WM_KEYDOWN, WM_SYSKEYDOWN]
    KEYS_UP   = (0x0101, 0x0105) # [WM_KEYUP, WM_SYSKEYUP]
    ALT_GRS   = (36, 64, 91, 92, 93, 123, 124, 125, 128, 163, 208, 222, 240, 254) # $@[\]{|}€£ŠŽšž
    OEM_KEYS  = {34: "Oem_3", 35: "Oem_5", 47: "Oem_1", 48: "Oem_2", 51: "Oem_5", 59: "Oem_Comma", 60: "Oem_Period", 61: "Oem_6", 94: "Oem_102"}
    STICKY_KEYS = ["Lcontrol", "Rcontrol", "Lshift", "Rshift", "Alt", "AltGr", "Lwin", "Rwin", "ScrollLock", "CapsLock", "NumLock"]



    def __init__(self, output):
        pykeyboard.PyKeyboardEvent.__init__(self)
        self._output = output
        NAMES = {"win32": "handler", "linux2": "tap", "darwin": "keypress"}
        HANDLERS = {"win32": self._handle_windows, "linux2": self._handle_linux,
                    "darwin": self._handle_mac}
        setattr(self, NAMES[sys.platform], HANDLERS[sys.platform])
        self._modifiers = dict((x, False) for x in self.MODIFIERNAMES.values())
        self._realmodifiers = dict((x, False) for x in self.MODIFIERNAMES)
        self._downs = {} # {key name: bool}
        self.start()


    def _keyname(self, key, keycode=None):
        if keycode in self.OEM_KEYS:
            key = self.OEM_KEYS[keycode]
        elif key.startswith("KP_"): # Linux numpad
            if 4 == len(key):
                key = key.replace("KP_", "Numpad")
            else:
                key = key.replace("KP_", "")
                key = "Numpad-" + self.RENAMES.get(key, key).replace("Numpad-", "")
        else:
            key = self.CONTROLCODES.get(key, key)
            key = self.RENAMES.get(key, key)
        return key.upper() if 1 == len(key) else key


    def _handle_windows(self, event):
        """Windows key event handler."""
        if event.Message not in self.KEYS_UP + self.KEYS_DOWN: return True
        vkey, is_altgr = self._keyname(event.GetKey()), False
        if vkey in self.MODIFIERNAMES:
            self._realmodifiers[vkey] = event.Message in self.KEYS_DOWN
            self._modifiers[self.MODIFIERNAMES[vkey]] = self._realmodifiers[vkey]
        if (vkey, event.IsExtended()) in self.NUMPAD_SPECIALS:
            key = vkey = "Numpad-" + vkey
        elif not event.Ascii or vkey.startswith("Numpad"):
            key = vkey
        else:
            is_altgr = event.Ascii in self.ALT_GRS
            key = self._keyname(unichr(event.Ascii))

        if vkey in self.STICKY_KEYS \
        and self._downs.get(vkey) == (event.Message in self.KEYS_DOWN):
            return True # Avoid multiple events on holding down Shift etc
        self._downs[vkey] = event.Message in self.KEYS_DOWN
        if not conf.KeyboardEnabled: return True
        if event.Message not in self.KEYS_DOWN:
            return True

        if DEBUG: print("Adding key %s (real %s)" % (key.encode("utf-8"), vkey.encode("utf-8")))
        self._output(type="keys", key=key, realkey=vkey)

        if vkey not in self.MODIFIERNAMES and not is_altgr and conf.KeyboardCombosEnabled:
            modifier = "-".join(k for k in ["Ctrl", "Alt", "Shift", "Win"]
                                if self._modifiers[k])
            if modifier and modifier != "Shift": # Shift-X is not a combo
                if self._modifiers["Ctrl"] and event.Ascii:
                    key = self._keyname(unichr(event.KeyID))
                realmodifier = "-".join(k for k, v in self._realmodifiers.items() if v)
                realkey = "%s-%s" % (realmodifier, key)
                key = "%s-%s" % (modifier, key)
                if DEBUG: print("Adding combo %s (real %s)" % (key.encode("utf-8"), realkey.encode("utf-8")))
                self._output(type="combos", key=key, realkey=realkey)

        if DEBUG:
            print("CHARACTER: %r" % key)
            print('GetKey: {0}'.format(event.GetKey()))  # Name of the virtual keycode, str
            print('IsAlt: {0}'.format(event.IsAlt()))  # Was the alt key depressed?, bool
            print('IsExtended: {0}'.format(event.IsExtended()))  # Is this an extended key?, bool
            print('IsInjected: {0}'.format(event.IsInjected()))  # Was this event generated programmatically?, bool
            print('IsTransition: {0}'.format(event.IsTransition()))  #Is this a transition from up to down or vice versa?, bool
            print('ASCII: {0}'.format(event.Ascii))  # ASCII value, if one exists, str
            print('KeyID: {0}'.format(event.KeyID))  # Virtual key code, int
            print('ScanCode: {0}'.format(event.ScanCode))  # Scan code, int
            print('Message: {0}'.format(event.Message))  # Name of the virtual keycode, str
            print()
        return True


    def _handle_mac(self, keycode):
        """Mac key event handler"""
        if not conf.KeyboardEnabled: return
        key = self._keyname(unichr(keycode))
        self._output(type="keys", key=key, realkey=key)

    def _handle_linux(self, keycode, character, press):
        """Linux key event handler."""
        if not conf.KeyboardEnabled: return
        if character is None: return
        key = self._keyname(character, keycode)
        if key in self.MODIFIERNAMES:
            self._modifiers[self.MODIFIERNAMES[key]] = press
            self._realmodifiers[key] = press
        if press:
            self._output(type="keys", key=key, realkey=key)
        if press and key not in self.MODIFIERNAMES and conf.KeyboardCombosEnabled:
            modifier = "-".join(k for k in ["Ctrl", "Alt", "Shift", "Win"]
                                if self._modifiers[k])
            if modifier and modifier != "Shift": # Shift-X is not a combo
                realmodifier = "-".join(k for k, v in self._realmodifiers.items() if v)
                realkey = "%s-%s" % (realmodifier, key)
                key = "%s-%s" % (modifier, key)
                if DEBUG: print("Adding combo %s (real %s)" % (key.encode("utf-8"), realkey.encode("utf-8")))
                self._output(type="combos", key=key, realkey=realkey)


    def escape(self, event):
        """Override PyKeyboardEvent.escape to not quit on Escape."""
        return False



class LineQueue(threading.Thread):
    """Reads lines from a file-like object and pushes to self.queue."""
    def __init__(self, input):
        threading.Thread.__init__(self)
        self.daemon = True
        self.input, self.queue = input, Queue.Queue()
        self.start()

    def run(self):
        for line in iter(self.input.readline, ""):
            self.queue.put(line.strip())


def start(inqueue, outqueue=None):
    """Starts the listener with incoming and outgoing queues."""
    conf.init(), db.init(conf.DbPath, conf.DbStatements)

    # Carry out db update for tables lacking expected new columns
    for (table, col), sqls in conf.DbUpdateStatements:
        if any(col == x["name"] for x in db.execute("PRAGMA table_info(%s)" % table)):
            continue # for
        for sql in sqls: db.execute(sql)

    try: Listener(inqueue, outqueue).run()
    except KeyboardInterrupt: pass


def main():
    """Entry point for stand-alone execution."""
    conf.init(), db.init(conf.DbPath)
    try: db.execute("PRAGMA journal_mode = WAL")
    except Exception: pass
    inqueue = LineQueue(sys.stdin).queue
    outqueue = type("", (), {"put": lambda self, x: print("\r%s" % x, end=" ")})()
    if "--quiet" in sys.argv: outqueue = None
    if conf.MouseEnabled:    inqueue.put("start mouse")
    if conf.KeyboardEnabled: inqueue.put("start keyboard")
    start(inqueue, outqueue)


if "__main__" == __name__:
    main()
