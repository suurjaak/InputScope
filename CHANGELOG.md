CHANGELOG
=========

1.6, 2022-02-28
---------------
- fix potential error on unplugging monitor (#12)
- take display index into account when discarding close mouse move events


1.5, 2022-01-22
---------------
- add named sessions functionality
- use unscaled screen size
- fix inactive table links on heatmaps for all time
- fix timedelta-seconds formatting
- full Python 2/3 compatibility


1.4.1, 2021-02-12
-----------------
- fixed error in database schema update, and scrolls-page statistics (issue #9)


1.4, 2021-02-11
---------------
- started using pynput instead of PyUserInput for input events
- started checking and saving changed screen size periodically


1.3, 2021-01-21
---------------
- all database writes in one process, using write-ahead log
- added individual event type toggles for mouse and keyboard input
- added options to clear history from the database
- added support for multiple displays in mouse heatmaps
- added single instance checker to ensure only one runtime per database
- added database information to web UI pages
- added max event limits to statistics and replay, avoiding page hangs
- added monthly statistics
- added collapse-toggles to days-section in input index
- added tray balloon notification on program startup
- added stop-link to replay
- optimized replay
- optimized program binary size
- decreased mouse move event counts
- upgraded wxPython to v4


1.1, 2015-05-22
---------------
- database optimizations to speed up web statistics significantly
- added day and table convenience links to statistics page


1.0, 2015-05-08
---------------
- first release
