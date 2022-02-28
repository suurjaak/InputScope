InputScope
==========

Mouse and keyboard input heatmap visualizer and statistics.

Runs a tray program that logs mouse and keyboard input events to a local database,
and provides a local web page for viewing statistics and heatmaps by day or month.

[![Mouse clicks heatmap](https://raw.githubusercontent.com/suurjaak/InputScope/media/th_clicks.png)](https://raw.githubusercontent.com/suurjaak/InputScope/media/clicks.png)
[![Mouse moves heatmap](https://raw.githubusercontent.com/suurjaak/InputScope/media/th_moves.png)](https://raw.githubusercontent.com/suurjaak/InputScope/media/moves.png)
[![Keyboard keys heatmap](https://raw.githubusercontent.com/suurjaak/InputScope/media/th_keys.png)](https://raw.githubusercontent.com/suurjaak/InputScope/media/keys.png)
[![Keyboard combos heatmap](https://raw.githubusercontent.com/suurjaak/InputScope/media/th_combos.png)](https://raw.githubusercontent.com/suurjaak/InputScope/media/combos.png)


Details
-------

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

* Python 2.7 or Python 3.5+
* bottle
* pynput
* wxPython (optional)

If wxPython is not available, InputScope will not have its tray program,
and will not recognize multi-monitor setups in mouse statistics.


Attribution
-----------

Heatmaps are drawn with heatmap.js,
released under the MIT License,
(c) 2014 Patrick Wied, http://www.patrick-wied.at/static/heatmapjs/.

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
