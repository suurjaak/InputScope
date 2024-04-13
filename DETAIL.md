Configuration
-------------

InputScope reads a number of settings from its configuration file at startup.

Some of them are exposed directly in the tray menu available on Windows;
all of them can be changed manually in the configuration file.


```ini
# Non-standard keyboard keys, as {numeric key code: "text label for key"},
# for providing or overriding key labels on statistics page.
# Example: {21: "IME Han/Yeong", 25: "IME Hanja"}
CustomKeys                = {}

# Default desktop screen size if not available from system,
# for scaling mouse events to heatmap, in pixels, as [width, height]
DefaultScreenSize         = [1920, 1080]

# Interval between logging input events to database, in seconds
EventsWriteInterval       = 5

# Heatmap library display settings, as {setting: value, input or event type: {..}}.
#
# "backgroundColor", default is transparent
# "blur", default 0.85
# "gradient", default {0.25: "blue", 0.55: "green", 0.85: "yellow", 1.0: "red"}
# "logScale", default false, true for keyboard
# "radius", default 20
# "opacity", default 0.6 (also "minOpacity" default 0, and "maxOpacity" default 1)
HeatmapDisplayOptions     = {"moves": {"radius": 10}, "clicks": {"radius": 15}}

# Maximum number of events to use for statistics page
MaxEventsForStats         = 1000000

# Maximum number of events to replay on statistics page
MaxEventsForReplay        = 100000

# Whether keyboard logging is enabled
KeyboardEnabled           = true

# Whether keyboard keypress event logging is enabled
KeyboardKeysEnabled       = true

# Whether keyboard key combination event logging is enabled
KeyboardCombosEnabled     = true

# Maximum keypress interval to count as one typing session, in seconds.
KeyboardSessionMaxDelta = 3

# Whether to ignore repeated keyboard events from long keypresses
KeyboardStickyEnabled     = true

# Maxinum number of most common keys/combos for applications on statistics page.
MaxTopKeysForPrograms = 5

# Whether mouse logging is enabled
MouseEnabled              = true

# Whether mouse move event logging is enabled
MouseMovesEnabled         = true

# Whether mouse click event logging is enabled
MouseClicksEnabled        = true

# Whether mouse scroll event logging is enabled
MouseScrollsEnabled       = true

# Size of mouse heatmap on statistics page, in pixels, as [width, height]
MouseHeatmapSize          = [640, 360]

# Maximum interval between linear move events for event reduction, in seconds (0 disables)
MouseMoveJoinInterval     = 0.5

# Fuzz radius for linear move events for event reduction, in heatmap-scale pixels
MouseMoveJoinRadius       = 5

# Maximum interval between scroll events for event reduction, in seconds (0 disables)
MouseScrollJoinInterval   = 0.5

# List of screen areas to monitor for mouse events if not all,
# as [[x, y, w, h], ] or [[screen index, [x, y, w, h]], ]; coordinates
# can be given as pixels, or as percentages of screen size (decimal fractions 0..1).
# Example to log mouse events from first screen only: [[0, [0, 0, 1.0, 1.0]]]
MouseRegionsOfInterest    = []

# List of screen areas to ignore for mouse events,
# as [[x, y, w, h], ] or [[screen index, [x, y, w, h]], ]; coordinates
# can be given as pixels, or as percentages of screen size (decimal fractions 0..1).
# Example to ignore mouse events from center of all screens: [[0.49, 0.49, 0.02, 0.02]]
MouseRegionsOfDisinterest = []

# Physical length of a pixel, for mouse event distance calculations, in meters
PixelLength               = 0.00024825

# Applications to ignore for inputs events,
# as {executable path: [] if all inputs else [input or event type, ]}.
# Path can be absolute or relative like "C:\Python\python.exe" or "python.exe",
# and can contain wildcards like "python*". Path is case-insensitive.
# Example to ignore keypress events from command prompts, and all mouse events from Paint:
# {"cmd.exe": ["keys"], "mspaint.exe": ["mouse"]}
ProgramBlacklist          = {}

# Applications to monitor inputs from if not all,
# as {executable path: [] if all inputs else [input or event type, ]}.
# Path can be absolute or relative like "C:\Python\python.exe" or "python.exe",
# and can contain wildcards like "python*". Path is case-insensitive.
# Example to monitor input events from Notepad only: {"notepad.exe": []}
ProgramWhitelist          = {}

# Whether active application logging, filtering and statistics are enabled
ProgramsEnabled           = True

# Interval between checking and saving changes in screen size, in seconds
ScreenSizeInterval        = 10

# HTTP port for the web user interface
WebPort                   = 8099
```
