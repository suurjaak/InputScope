InputScope
==========

Mouse and keyboard input heatmap visualizer and statistics.

Three components:
* main - wxPython desktop tray program, runs listener and webui
* listener - logs mouse and keyboard input, can run individually
* webui - web frontend for statistics and heatmaps, can run individually

Listener and web-UI components can be run separately, or launched from main.

Data is kept in an SQLite database, under inputscope/var.

[![Mouse heatmap](https://raw.github.com/suurjaak/InputScope/media/th_mouse.png)](https://raw.github.com/suurjaak/InputScope/media/mouse.png)
[![Keyboard heatmap](https://raw.github.com/suurjaak/InputScope/media/th_keyboard.png)](https://raw.github.com/suurjaak/InputScope/media/keyboard.png)


Installation
------------

Works best on Windows, tested on Linux, might work on Mac.

Windows: download and launch the latest release from
http://github.com/suurjaak/InputScope/releases.

Or:
`pip install inputscope`

The pip installation will add commands `inputscope`, `inputscope-listener` 
and `inputscope-webui` command to path.


Dependencies
------------

* Python 2.6 or 2.7
* bottle
* PyUserInput
* wxPython (optional)


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
