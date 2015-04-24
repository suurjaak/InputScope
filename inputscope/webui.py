# -*- coding: utf-8 -*-
"""
Web frontend interface, displays statistics from a database.

@author      Erki Suurjaak
@created     06.04.2015
@modified    24.04.2015
"""
import collections
import datetime
import math
import os
import bottle
from bottle import hook, request, route

import conf
import db

app = None   # Bottle application instance


@hook("before_request")
def before_request():
    """Set up convenience variables, remove trailing slashes from route."""
    request.environ["PATH_INFO"] = request.environ["PATH_INFO"].rstrip("/")


@route("/static/<filepath:path>")
def server_static(filepath):
    """Handler for serving static files."""
    mimetype = "image/svg+xml" if filepath.endswith(".svg") else "auto"
    return bottle.static_file(filepath, root=conf.StaticPath, mimetype=mimetype)


@route("/mouse/<table>")
@route("/mouse/<table>/<day>")
def mouse(table, day=None):
    """Handler for showing mouse statistics for specified type and day."""
    where = (("DATE(dt)", day),) if day else ()
    events = db.fetch(table, where=where, order=("dt",))
    stats, positions, events = stats_mouse(events, table)
    return bottle.template("mouse.tpl", locals(), apptitle=conf.Title)


@route("/keyboard/<table>")
@route("/keyboard/<table>/<day>")
def keyboard(table, day=None):
    """Handler for showing the keyboard statistics page."""
    where = (("DATE(dt)", day),) if day else ()
    cols, group = "key, realkey, COUNT(*) AS total", "key, realkey"
    counts = db.fetch(table, cols, where=where, group=group, order=(("total", "DESC"),))
    events = db.fetch(table, where=where, order=("id",))
    stats, collatedevents = stats_keyboard(events, table)
    return bottle.template("keyboard.tpl", locals(), apptitle=conf.Title)


@route("/<input>")
def inputindex(input):
    """Handler for showing keyboard or mouse page with day and total links."""
    stats = {}
    countminmax = "COUNT(*) AS total, MIN(DATE(dt)) AS first, MAX(DATE(dt)) AS last"
    dtcountcols, dtcountgroup, dtcountorder = "DATE(dt) AS day, COUNT(*) AS total", "day", ("day",)
    tables = ("moves", "clicks", "scrolls") if "mouse" == input else ("keys", "combos")
    for table in tables:
        stats[table] = db.fetchone(table, countminmax)
        stats[table]["days"] = db.fetch(table, dtcountcols, group=dtcountgroup, order=dtcountorder)
    return bottle.template("input.tpl", locals(), apptitle=conf.Title)


@route("/")
def index():
    """Handler for showing the GUI index page."""
    stats = {"mouse": {"total": 0}}
    countminmax = "COUNT(*) AS total, MIN(DATE(dt)) AS first, MAX(DATE(dt)) AS last"
    stats["keyboard"] = db.fetchone("keys", countminmax)
    for table in ("moves", "clicks", "scrolls"):
        row = db.fetchone(table, countminmax)
        if not row["total"]: continue # for table
        stats["mouse"]["total"] += row["total"]
        for func, key in ([min, "first"], [max, "last"]):
            stats["mouse"][key] = row[key] if key not in stats["mouse"] \
                                  else func(stats["mouse"][key], row[key])
    return bottle.template("index.tpl", locals(), apptitle=conf.Title)


def stats_keyboard(events, table):
    """Return statistics and collated events for keyboard events."""
    if len(events) < 2: return [], []
    deltas, prev_dt = [], None
    sessions, session = [], None
    UNBROKEN_DELTA = datetime.timedelta(seconds=conf.KeyboardSessionMaxDelta)
    blank = collections.defaultdict(lambda: collections.defaultdict(int))
    collated = [blank.copy()] # [{dt, keys: {key: count}}]
    for e in events:
        if prev_dt:
            if prev_dt.second != e["dt"].second or prev_dt.minute != e["dt"].minute or prev_dt.hour != e["dt"].hour:
                collated.append(blank.copy())
            delta = e["dt"] - prev_dt
            deltas.append(delta)
            if delta > UNBROKEN_DELTA:
                session = None
            else:
                if not session:
                    session = []
                    sessions.append(session)
                session.append(delta)
        collated[-1]["dt"] = e["dt"]
        collated[-1]["keys"][e["realkey"]] += 1
        prev_dt = e["dt"]
    longest_session = max(sessions, key=lambda x: sum(x, datetime.timedelta()))
    stats = [
        ("Average interval between combos",
         sum(deltas, datetime.timedelta()) / len(deltas)),
    ] if "combos" == table else [
        ("Keys per hour",
         int(len(events) / ((events[-1]["dt"] - events[0]["dt"]).total_seconds() / 3600))),
        ("Average interval between keys",
         sum(deltas, datetime.timedelta()) / len(deltas)),
        ("Typing sessions (key interval < %ss)" % UNBROKEN_DELTA.seconds,
         len(sessions)),
        ("Average keys in session",
         sum(len(x) + 1 for x in sessions) / len(sessions)),
        ("Average session duration", sum((sum(x, datetime.timedelta())
         for x in sessions), datetime.timedelta()) / len(sessions)),
        ("Longest session duration",
         sum(longest_session, datetime.timedelta())),
        ("Keys in longest session",
         len(longest_session) + 1),
        ("Most keys in session",
         max(len(x) + 1 for x in sessions)),
    ]
    return stats, collated


def stats_mouse(events, table):
    """Returns statistics, positions and rescaled events for mouse events."""
    distance, last = 0, None
    HS = conf.MouseHeatmapSize
    SC = dict(("xy"[i], conf.DefaultScreenSize[i] / float(HS[i])) for i in [0, 1])
    xymap = collections.defaultdict(int)
    sizes = db.fetch("screen_sizes", order=("dt",))
    sizeidx, sizelen = -1, len(sizes) # Scale by desktop size at event time
    for e in events:
        if last:
            distance += math.sqrt(sum(abs(e[k] - last[k])**2 for k in "xy"))
        last = dict(e) if "moves" == table else None
        if sizeidx < 0: # Find latest size from before event
            for i, size in reversed(list(enumerate(sizes))):
                if e["dt"] >= size["dt"]:
                    SC = dict((k, size[k] / float(HS["y" == k])) for k in "xy")
                    sizeidx = i
                    break # for i, size
        else: # Find next size from before event
            while sizeidx < sizelen - 2 and e["dt"] >= sizes[sizeidx + 1]["dt"]:
                sizeidx += 1
            if sizeidx < sizelen - 1 and e["dt"] >= sizes[sizeidx]["dt"]:
                SC = dict((k, sizes[sizeidx][k] / float(HS["y" == k])) for k in "xy")
        e["x"], e["y"] = tuple(min(int(e[k] / SC[k]), HS["y" == k]) for k in "xy")
        xymap[(e["x"], e["y"])] += 1

    stats, positions = [], [dict(x=x, y=y, count=v) for (x, y), v in xymap.items()]
    if "moves" == table:
        stats = [("Distance in pixels", "{0:,}px".format(int(math.ceil(distance)))),
                 ("Distance in meters", "%.1fm (if pixel is %smm)" 
                  % (distance * conf.PixelLength, conf.PixelLength * 1000))]
    return stats, positions, events


def init():
    """Initialize configuration and web application."""
    global app
    if app: return app
    conf.init()
    db.init(conf.DbPath, conf.DbStatements)

    bottle.TEMPLATE_PATH.insert(0, conf.TemplatePath)
    app = bottle.default_app()
    bottle.BaseTemplate.defaults.update(get_url=app.get_url)
    return app


def start():
    """Starts the web server."""
    global app
    bottle.run(app, host="localhost", port=conf.WebPort,
               debug=conf.WebAutoReload, reloader=conf.WebAutoReload,
               quiet=conf.WebQuiet)


app = init()


if "__main__" == __name__:
    conf.WebAutoReload, conf.WebQuiet = True, False
    start()
