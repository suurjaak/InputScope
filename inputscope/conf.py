# -*- coding: utf-8 -*-
"""
Configuration settings. Can read additional/overridden options from INI file,
supporting any JSON-serializable datatype.

INI file can contain a [DEFAULT] section for default settings, and additional
sections overriding the default for different environments. Example:
-----------------
[DEFAULT]
# single-line comments can start with # or ;
ServerIP = my.server.domain
ServerPort = 80
SampleJSON = {"a": false, "b": [0.1, 0.2]}

[DEV]
ServerIP = 0.0.0.0

save() retains only the DEFAULT section, and writes only values diverging from
the declared ones in source code. File is deleted if all values are at default.

@author      Erki Suurjaak
@created     26.03.2015
@modified    06.05.2015
------------------------------------------------------------------------------
"""
try: import ConfigParser as configparser # Py2
except ImportError: import configparser  # Py3
try: import cStringIO as StringIO         # Py2
except ImportError: import io as StringIO # Py3
import datetime
import json
import logging
import os
import re
import sys

"""Program title, version number and version date."""
Title = "InputScope"
Version = "1.0"
VersionDate = "06.05.2015"

"""TCP port of the web user interface."""
WebHost = "localhost"
WebPort = 8099
WebUrl = "http://%s:%s" % (WebHost, WebPort)

HomepageUrl = "https://github.com/suurjaak/InputScope"

"""Size of the heatmaps, in pixels."""
MouseHeatmapSize = (640, 360)
KeyboardHeatmapSize = (680, 180)

"""Default desktop size for scaling, if not available from system, in pixels."""
DefaultScreenSize = (1920, 1080)

"""Whether mouse or keyboard logging is enabled."""
MouseEnabled = True
KeyboardEnabled = True

"""Maximum keypress interval to count as one typing session, in seconds."""
KeyboardSessionMaxDelta = 3

"""Physical length of a pixel, in meters."""
PixelLength = 0.00024825

"""Key positions in keyboard heatmap."""
KeyPositions = {
  "Escape": (12, 12),
  "F1": (72, 12),
  "F2": (102, 12),
  "F3": (132, 12),
  "F4": (162, 12),
  "F5": (206, 12),
  "F6": (236, 12),
  "F7": (266, 12),
  "F8": (296, 12),
  "F9": (338, 12),
  "F10": (368, 12),
  "F11": (398, 12),
  "F12": (428, 12),
  "PrintScreen": (472, 12),
  "ScrollLock": (502, 12),
  "Pause": (532, 12),
  "Break": (532, 12),

  "Oem_7": (12, 56),
  "1": (44, 56),
  "2": (74, 56),
  "3": (104, 56),
  "4": (134, 56),
  "5": (164, 56),
  "6": (192, 56),
  "7": (222, 56),
  "8": (252, 56),
  "9": (281, 56),
  "0": (311, 56),
  "Oem_Minus": (340, 56),
  "Oem_Plus": (371, 56),
  "Backspace": (414, 56),

  "Tab": (24, 84),
  "Q": (60, 84),
  "W": (90, 84),
  "E": (120, 84),
  "R": (150, 84),
  "T": (180, 84),
  "Y": (210, 84),
  "U": (240, 84),
  "I": (270, 84),
  "O": (300, 84),
  "P": (330, 84),
  "Oem_3": (360, 84),
  "Oem_4": (390, 84),
  "Enter": (426, 96),

  "CapsLock": (25, 111),
  "A": (68, 111),
  "S": (98, 111),
  "D": (128, 111),
  "F": (158, 111),
  "G": (188, 111),
  "H": (218, 111),
  "J": (248, 111),
  "K": (278, 111),
  "L": (308, 111),
  "Oem_1": (338, 111),
  "Oem_2": (368, 111),
  "Oem_5": (394, 111),

  "Lshift": (19, 138),
  "Oem_102": (50, 138),
  "Z": (80, 138),
  "X": (110, 138),
  "C": (140, 138),
  "V": (170, 138),
  "B": (200, 138),
  "N": (230, 138),
  "M": (260, 138),
  "Oem_Comma": (290, 138),
  "Oem_Period": (320, 138),
  "Oem_6": (350, 138),
  "Rshift": (404, 138),

  "Lcontrol": (19, 166),
  "Lwin": (54, 166),
  "Alt": (89, 166),
  "Space": (201, 166),
  "AltGr": (315, 166),
  "Rwin": (350, 166),
  "Menu": (384, 166),
  "Rcontrol": (424, 166),

  "Up": (504, 138),
  "Left": (474, 166),
  "Down": (504, 166),
  "Right": (534, 166),

  "Insert": (474, 56),
  "Home": (504, 56),
  "PageUp": (534, 56),
  "Delete": (474, 84),
  "End": (504, 84),
  "PageDown": (534, 84),

  "NumLock": (576, 56),
  "Numpad-Divide": (605, 56),
  "Numpad-Multiply": (634, 56),
  "Numpad-Subtract": (664, 56),
  "Numpad-Add": (664, 98),
  "Numpad-Enter": (664, 152),
  "Numpad0": (590, 166),
  "Numpad1": (576, 138),
  "Numpad2": (605, 138),
  "Numpad3": (634, 138),
  "Numpad4": (576, 111),
  "Numpad5": (605, 111),
  "Numpad6": (634, 111),
  "Numpad7": (576, 84),
  "Numpad8": (605, 84),
  "Numpad9": (634, 84),
  "Numpad-Insert": (590, 166),
  "Numpad-Decimal": (634, 166),
  "Numpad-Delete": (634, 166),
  "Numpad-End": (576, 138),
  "Numpad-Down": (605, 138),
  "Numpad-PageDown": (634, 138),
  "Numpad-Left": (576, 111),
  "Numpad-Clear": (605, 111),
  "Numpad-Right": (634, 111),
  "Numpad-Home": (576, 84),
  "Numpad-Up": (605, 84),
  "Numpad-PageUp": (634, 84),
}

"""Whether web modules and templates are automatically reloaded on change."""
WebAutoReload = False

"""Whether web server is quiet or echoes access log."""
WebQuiet = False

"""Whether running as a pyinstaller executable."""
Frozen = getattr(sys, "frozen", False)
if Frozen:
    ExecutablePath = ShortcutIconPath = os.path.abspath(sys.executable)
    ApplicationPath = os.path.dirname(ExecutablePath)
    RootPath = os.path.join(os.environ.get("_MEIPASS2", getattr(sys, "_MEIPASS", "")))
    DbPath = os.path.join(ApplicationPath, "%s.db" % Title.lower())
    ConfigPath = os.path.join(ApplicationPath, "%s.ini" % Title.lower())
else:
    RootPath = ApplicationPath = os.path.dirname(os.path.abspath(__file__))
    ExecutablePath = os.path.join(RootPath, "main.py")
    ShortcutIconPath = os.path.join(RootPath, "static", "icon.ico")
    DbPath = os.path.join(RootPath, "var", "%s.db" % Title.lower())
    ConfigPath = os.path.join(ApplicationPath, "var", "%s.ini" % Title.lower())

"""Path for static web content, like images and JavaScript files."""
StaticPath = os.path.join(RootPath, "static")

"""Path for HTML templates."""
TemplatePath = os.path.join(RootPath, "views")

"""Path for application icon file."""
IconPath = os.path.join(StaticPath, "icon.ico")

"""Statements to execute in database at startup, like CREATE TABLE."""
DbStatements = (
  "CREATE TABLE IF NOT EXISTS moves (id INTEGER NOT NULL PRIMARY KEY, dt TIMESTAMP, x INTEGER, y INTEGER)",
  "CREATE TABLE IF NOT EXISTS clicks (id INTEGER NOT NULL PRIMARY KEY, dt TIMESTAMP, x INTEGER, y INTEGER, button INTEGER)",
  "CREATE TABLE IF NOT EXISTS scrolls (id INTEGER NOT NULL PRIMARY KEY, dt TIMESTAMP, x INTEGER, y INTEGER, wheel INTEGER)",
  "CREATE TABLE IF NOT EXISTS keys (id INTEGER NOT NULL PRIMARY KEY, dt TIMESTAMP, key TEXT, realkey TEXT)",
  "CREATE TABLE IF NOT EXISTS combos (id INTEGER NOT NULL PRIMARY KEY, dt TIMESTAMP, key TEXT, realkey TEXT)",
  "CREATE TABLE IF NOT EXISTS app_events (id INTEGER NOT NULL PRIMARY KEY, dt TIMESTAMP DEFAULT (DATETIME('now', 'localtime')), type TEXT)",
  "CREATE TABLE IF NOT EXISTS screen_sizes (id INTEGER NOT NULL PRIMARY KEY, dt TIMESTAMP DEFAULT (DATETIME('now', 'localtime')), x INTEGER, y INTEGER)",
)


def init(filename=ConfigPath):
    """Loads INI configuration into this module's attributes."""
    section, parts = "DEFAULT", filename.rsplit(":", 1)
    if len(parts) > 1 and os.path.isfile(parts[0]): filename, section = parts
    if not os.path.isfile(filename): return

    vardict, parser = globals(), configparser.RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    try:
        def parse_value(raw):
            try: return json.loads(raw) # Try to interpret as JSON
            except ValueError: return raw # JSON failed, fall back to raw
        txt = open(filename).read() # Add DEFAULT section if none present
        if not re.search("\\[\\w+\\]", txt): txt = "[DEFAULT]\n" + txt
        parser.readfp(StringIO.StringIO(txt), filename)
        for k, v in parser.items(section): vardict[k] = parse_value(v)
    except Exception:
        logging.warn("Error reading config from %s.", filename, exc_info=True)


def save(filename=ConfigPath):
    """Saves this module's changed attributes to INI configuration."""
    default_values = defaults()
    parser = configparser.RawConfigParser()
    parser.optionxform = str # Force case-sensitivity on names
    try:
        save_types = basestring, int, float, tuple, list, dict, type(None)
        for k, v in sorted(globals().items()):
            if not isinstance(v, save_types) or k.startswith("_") \
            or default_values.get(k, parser) == v: continue # for k, v
            try: parser.set("DEFAULT", k, json.dumps(v))
            except Exception: pass
        if parser.defaults():
            with open(filename, "wb") as f:
                f.write("# %s %s configuration written on %s.\n" % (Title, Version,
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                parser.write(f)
        else: # Nothing to write: delete configuration file
            try: os.unlink(filename)
            except Exception: pass
    except Exception:
        logging.warn("Error writing config to %s.", filename, exc_info=True)


def defaults(values={}):
    """Returns a once-assembled dict of this module's storable attributes."""
    if values: return values
    save_types = basestring, int, float, tuple, list, dict, type(None)
    for k, v in globals().items():
        if isinstance(v, save_types) and not k.startswith("_"): values[k] = v
    return values


defaults() # Store initial values to compare on saving
