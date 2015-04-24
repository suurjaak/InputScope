InputOut
========

Mouse and keyboard input visualizer.

Three components:
* main - wxPython desktop tray program, runs listener and webui
* listener - listens and logs mouse and keyboard input
* webui - web frontend for statistics and heatmaps

Listener and web-UI components can be run separately, or launched from main.

[screenshot @todo mouse]
[screenshot @todo keyboard]


Dependencies
------------

* Python 2.7
* bottle
* PyUserInput
* wxPython (optional)


Attribution
-----------

Heatmaps are drawn with heatmap.js,
(c) 2014 Patrick Wied, http://www.patrick-wied.at/static/heatmapjs/.

Icon from Paomedia small-n-flat iconset,
released under Creative Commons (Attribution 3.0 Unported),
https://www.iconfinder.com/icons/285642/monitor_icon.
