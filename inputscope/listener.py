# -*- coding: utf-8 -*-
"""
Mouse and keyboard listener, logs events to database.

--quiet      prints out nothing

@author      Erki Suurjaak
@created     06.04.2015
@modified    07.05.2015
"""
from __future__ import print_function
import datetime
import Queue
import sys
import threading
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
        self.key_handler = None
        self.data_handler = DataHandler(getattr(outqueue, "put", lambda x: x))

    def run(self):
        self.running = True
        while self.running:
            command = self.inqueue.get()
            if "exit" == command:
                self.stop()
            elif "mouse_start" == command:
                if not self.mouse_handler:
                    self.mouse_handler = MouseHandler(self.data_handler.handle)
            elif "mouse_stop" == command:
                if self.mouse_handler:
                    self.mouse_handler = self.mouse_handler.stop()
            elif "keyboard_start" == command:
                if not self.key_handler:
                    self.key_handler = KeyHandler(self.data_handler.handle)
            elif "keyboard_stop" == command:
                if self.key_handler:
                    self.key_handler = self.key_handler.stop()

    def stop(self):
        self.running = False
        self.mouse_handler and self.mouse_handler.stop()
        self.key_handler and self.key_handler.stop()
        self.data_handler.stop()
        self.inqueue.put(None) # Wake up thread waiting on queue



class DataHandler(threading.Thread):
    """Output thread, inserts events to database and to output function."""
    def __init__(self, output):
        threading.Thread.__init__(self)
        self.counts = {} # {type: count}
        self.output = output
        self.inqueue = Queue.Queue()
        self.lasts = {"moves": None}
        self.running = False
        self.start()

    def run(self):
        self.running = True
        dbqueue = [] # Data queued for later after first insert failed
        db.insert("app_events", type="start")
        while self.running:
            data = self.inqueue.get()
            if not data: continue # while self.running

            event = data.pop("type")
            if event in self.lasts: # Skip event if same position as last
                pos = data["x"], data["y"]
                if self.lasts[event] == pos: continue # while self.running
                self.lasts[event] = pos

            if event not in self.counts: self.counts[event] = 0
            self.counts[event] += 1
            dbqueue.append((event, data))
            try:
                for item in dbqueue:
                    db.insert(*item), dbqueue.remove(item)
            except Exception as e:
                print(e, event, data)
            self.output(self.counts)

    def stop(self):
        self.running = False
        self.inqueue.put(None) # Wake up thread waiting on queue
        db.close()

    def handle(self, **kwargs):
        kwargs["dt"] = datetime.datetime.now()
        self.inqueue.put(kwargs)



class MouseHandler(pymouse.PyMouseEvent):
    """Listens to mouse events and forwards to output."""

    def __init__(self, output):
        pymouse.PyMouseEvent.__init__(self)
        self._output = output
        self.start()

    def click(self, x, y, button, press):
        if press: self._output(type="clicks", x=x, y=y, button=button)

    def move(self, x, y):
        self._output(type="moves", x=x, y=y)

    def scroll(self, x, y, wheel):
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



    def __init__(self, output):
        pykeyboard.PyKeyboardEvent.__init__(self)
        self._output = output
        NAMES = {"win32": "handler", "linux2": "tap", "darwin": "keypress"}
        HANDLERS = {"win32": self._handle_windows, "linux2": self._handle_linux,
                    "darwin": self._handle_mac}
        setattr(self, NAMES[sys.platform], HANDLERS[sys.platform])
        self._modifiers = dict((x, False) for x in self.MODIFIERNAMES.values())
        self._realmodifiers = dict((x, False) for x in self.MODIFIERNAMES)
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
        vkey = self._keyname(event.GetKey())
        if event.Message in self.KEYS_UP + self.KEYS_DOWN:
            if vkey in self.MODIFIERNAMES:
                self._realmodifiers[vkey] = event.Message in self.KEYS_DOWN
                self._modifiers[self.MODIFIERNAMES[vkey]] = self._realmodifiers[vkey]
        if event.Message not in self.KEYS_DOWN:
            return True

        is_altgr = False
        if (vkey, event.IsExtended()) in self.NUMPAD_SPECIALS:
            key = vkey = "Numpad-" + vkey
        elif not event.Ascii or vkey.startswith("Numpad"):
            key = vkey
        else:
            is_altgr = event.Ascii in self.ALT_GRS
            key = self._keyname(unichr(event.Ascii))

        if DEBUG: print("Adding key %s (real %s)" % (key.encode("utf-8"), vkey.encode("utf-8")))
        self._output(type="keys", key=key, realkey=vkey)

        if vkey not in self.MODIFIERNAMES and not is_altgr:
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
        key = self._keyname(unichr(keycode))
        self._output(type="keys", key=key, realkey=key)

    def _handle_linux(self, keycode, character, press):
        """Linux key event handler."""
        if character is None: return
        key = self._keyname(character, keycode)
        if key in self.MODIFIERNAMES:
            self._modifiers[self.MODIFIERNAMES[key]] = press
            self._realmodifiers[key] = press
        if press:
            self._output(type="keys", key=key, realkey=key)
        if press and key not in self.MODIFIERNAMES:
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
    conf.init(), db.init(conf.DbPath)
    Listener(inqueue, outqueue).run()


def main():
    """Entry point for stand-alone execution."""
    conf.init(), db.init(conf.DbPath)
    inqueue = LineQueue(sys.stdin).queue
    outqueue = type("", (), {"put": lambda self, x: print("\r%s" % x, end=" ")})()
    if "--quiet" in sys.argv: outqueue = None
    if conf.MouseEnabled:    inqueue.put("mouse_start")
    if conf.KeyboardEnabled: inqueue.put("keyboard_start")
    start(inqueue, outqueue)


if "__main__" == __name__:
    main()
