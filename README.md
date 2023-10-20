InputScope
==========

Mouse and keyboard input heatmap visualizer and statistics.

Runs a tray program that logs mouse and keyboard input events to a local database,
and provides a local web page for viewing statistics and heatmaps by day or month.

[![Mouse clicks heatmap](https://raw.githubusercontent.com/suurjaak/InputScope/media/th_clicks.png)](https://raw.githubusercontent.com/suurjaak/InputScope/media/clicks.png)
[![Mouse moves heatmap](https://raw.githubusercontent.com/suurjaak/InputScope/media/th_moves.png)](https://raw.githubusercontent.com/suurjaak/InputScope/media/moves.png)
[![Keyboard keys heatmap](https://raw.githubusercontent.com/suurjaak/InputScope/media/th_keys.png)](https://raw.githubusercontent.com/suurjaak/InputScope/media/keys.png)
[![Keyboard combos heatmap](https://raw.githubusercontent.com/suurjaak/InputScope/media/th_combos.png)](https://raw.githubusercontent.com/suurjaak/InputScope/media/combos.png)


Overview
--------

Logs mouse clicks and scrolls and movement, and keyboard key presses and key 
combinations; event categories can be toggled off from tray menu.

Provides an option to record named sessions, allowing to group inputs
with finer detail than one day.

Keypresses are logged as physical keys, ignoring Unicode mappings.
Note: keyboard logging can interfere with remote control desktop, 
UI automation scripts, and sticky keys.

Data is kept in an SQLite database.

The local web page is viewable at http://localhost:8099/,
port can be changed in configuration file.


### Configuration

Specific applications to monitor can be blacklisted
or whitelisted in configuration file, as:
```python
# Path can be absolute or relative like "C:\Python\python.exe" or "python.exe",
# and can contain wildcards like "python*".
ProgramBlacklist = {executable path: [] if all inputs else [input or event type, ]}
ProgramWhitelist = {executable path: [] if all inputs else [input or event type, ]}
```
e.g.
```python
# Monitor all inputs from Notepad only
ProgramWhitelist = {"notepad.exe": []}
```
or
```python
# Ignore keypress events from command prompts, and all mouse events from Paint.
ProgramBlacklist = {"cmd.exe": ["keys"], "mspaint.exe": ["mouse"]}
```

Non-standard keys can be added in configuration file, as:
```python
CustomKeys = {numeric key code: "text label for key"}
```
e.g.
```python
CustomKeys = {21: "IME Han/Yeong", 25: "IME Hanja"}
```

Screen areas to monitor for mouse events can be specified in configuration file,
allowing to log events from specific areas only or to skip events from blacklisted areas:
```python
# Coordinates given as pixels, or as percentages of screen size (decimal fractions 0..1).
MouseRegionsOfInterest    = [[x, y, w, h], ] or [[screen index, [x, y, w, h]], ]
MouseRegionsOfDisinterest = [[x, y, w, h], ] or [[screen index, [x, y, w, h]], ]
```
e.g.
```python
# Ignore mouse events from center of all screens
MouseRegionsOfDisinterest = [[0.49, 0.49, 0.02, 0.02]]
```

For more on configuration settings, see [DETAIL.md](DETAIL.md).


Installation
------------

Works best on Windows, tested on Linux, might work on Mac.

Windows: download and launch the latest release from
http://github.com/suurjaak/InputScope/releases.

Or:
`pip install inputscope`

Three components in source code form:
* main - wxPython desktop tray program, runs listener and webui
* listener - logs mouse and keyboard input, can run individually
* webui - web frontend for statistics and heatmaps, can run individually

Listener and web-UI components can be run separately.

In source code form, data and configuration is kept under `inputscope/var`.

The pip installation will add commands `inputscope`, `inputscope-listener` 
and `inputscope-webui` to path.


Dependencies
------------

* Python 2.7 or Python 3.5+ (https://www.python.org)
* bottle (https://pypi.org/project/bottle)
* psutil (https://pypi.org/project/psutil)
* pynput (https://pypi.org/project/pynput)
* pywin32 (optional, for toggling "Start with Windows") (https://pypi.org/project/pywin32)
* wxPython (optional) (https://wxpython.org)

If wxPython is not available, InputScope will not have its tray program,
and will not recognize multi-monitor setups in mouse statistics.

For application statistics in Linux, the `x11-utils` system package needs to be installed.


Attribution
-----------

Heatmaps are drawn with heatmap.js,
released under the MIT License,
(c) 2014 Patrick Wied, https://github.com/pa7/heatmap.js.

Icon from Paomedia small-n-flat iconset,
released under Creative Commons (Attribution 3.0 Unported),
https://www.iconfinder.com/icons/285642/monitor_icon.

Keyboard image modified from Wikipedia `File:ISO keyboard (105) QWERTY UK.svg`,
released under the GNU Free Documentation License,
http://en.wikipedia.org/wiki/File:ISO_keyboard_(105)_QWERTY_UK.svg.


License
-------

Copyright (C) 2015 by Erki Suurjaak.
Released as free open source software under the MIT License,
see [LICENSE.md](LICENSE.md).
