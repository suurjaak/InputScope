# -*- coding: utf-8 -*-
"""
Web frontend interface, displays statistics from a database.

--quiet      prints out nothing

@author      Erki Suurjaak
@created     06.04.2015
@modified    16.06.2015
"""
import collections
import datetime
import math
import re
import sys
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
    where = (("day", day),) if day else ()
    events = db.select(table, where=where, order="day")
    stats, positions, count, events = stats_mouse(events, table)
    days, input = db.fetch("counts", order="day", type=table), "mouse"
    tabledays = set(x["type"] for x in db.fetch("counts", day=day)) if day else {}
    return bottle.template("heatmap.tpl", locals(), conf=conf)


@route("/keyboard/<table>")
@route("/keyboard/<table>/<day>")
def keyboard(table, day=None):
    """Handler for showing the keyboard statistics page."""
    cols, group = "realkey AS key, COUNT(*) AS count", "realkey"
    where = (("day", day),) if day else ()
    counts_display = counts = db.fetch(table, cols, where, group, "count DESC")
    if "combos" == table:
        counts_display = db.fetch(table, "key, COUNT(*) AS count", where,
                                  "key", "count DESC")
    events = db.fetch(table, where=where, order="stamp")
    for e in events: e["dt"] = datetime.datetime.fromtimestamp(e["stamp"])
    stats, collatedevents, count = stats_keyboard(events, table)
    days, input = db.fetch("counts", order="day", type=table), "keyboard"
    tabledays = set(x["type"] for x in db.fetch("counts", day=day)) if day else {}
    return bottle.template("heatmap.tpl", locals(), conf=conf)


@route("/<input>")
def inputindex(input):
    """Handler for showing keyboard or mouse page with day and total links."""
    stats = {}
    countminmax = "SUM(count) AS count, MIN(day) AS first, MAX(day) AS last"
    tables = ("moves", "clicks", "scrolls") if "mouse" == input else ("keys", "combos")
    for table in tables:
        stats[table] = db.fetchone("counts", countminmax, type=table)
        stats[table]["days"] = db.fetch("counts", order="day DESC", type=table)
    return bottle.template("input.tpl", locals(), conf=conf)


@route("/")
def index():
    """Handler for showing the GUI index page."""
    stats = dict((k, {"count": 0}) for k, tt in conf.InputTables)
    countminmax = "SUM(count) AS count, MIN(day) AS first, MAX(day) AS last"
    for input, table in [(x, t) for x, tt in conf.InputTables for t in tt]:
        row = db.fetchone("counts", countminmax, type=table)
        if not row["count"]: continue # for input, table
        stats[input]["count"] += row["count"]
        for func, key in [(min, "first"), (max, "last")]:
            stats[input][key] = (row[key] if key not in stats[input]
                                 else func(stats[input][key], row[key]))
    return bottle.template("index.tpl", locals(), conf=conf)


def stats_keyboard(events, table):
    """Return (statistics, collated events, total count) for keyboard events."""
    if len(events) < 2: return [], []
    deltas, prev_dt = [], None
    sessions, session = [], None
    UNBROKEN_DELTA = datetime.timedelta(seconds=conf.KeyboardSessionMaxDelta)
    blank = collections.defaultdict(lambda: collections.defaultdict(int))
    collated = [blank.copy()] # [{dt, keys: {key: count}}]
    for e in events:
        if prev_dt:
            if (prev_dt.second != e["dt"].second
            or prev_dt.minute != e["dt"].minute or prev_dt.hour != e["dt"].hour):
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
    longest_session = max(sessions + [[datetime.timedelta()]], key=lambda x: sum(x, datetime.timedelta()))
    stats = [
        ("Average combo interval",
         format_timedelta(sum(deltas, datetime.timedelta()) / len(deltas))),
    ] if "combos" == table else [
        ("Keys per hour",
         int(3600 * len(events) / timedelta_seconds(events[-1]["dt"] - events[0]["dt"]))),
        ("Average key interval",
         format_timedelta(sum(deltas, datetime.timedelta()) / len(deltas))),
        ("Typing sessions (key interval < %ss)" % UNBROKEN_DELTA.seconds,
         len(sessions)),
        ("Average keys in session",
         sum(len(x) + 1 for x in sessions) / len(sessions)),
        ("Average session duration", format_timedelta(sum((sum(x, datetime.timedelta())
         for x in sessions), datetime.timedelta()) / len(sessions))),
        ("Longest session duration",
         format_timedelta(sum(longest_session, datetime.timedelta()))),
        ("Keys in longest session",
         len(longest_session) + 1),
        ("Most keys in session",
         max(len(x) + 1 for x in sessions)),
    ]
    stats += [("Total time interval", format_timedelta(events[-1]["dt"] - events[0]["dt"]))]
    return stats, collated, len(events)



def stats_mouse(events, table):
    """Returns (statistics, positions, event count, events if not "moves")."""
    distance, first, last, totaldelta = 0, None, None, datetime.timedelta()
    count, all_events = 0, []
    HS = conf.MouseHeatmapSize
    SC = dict(("xy"[i], conf.DefaultScreenSize[i] / float(HS[i])) for i in [0, 1])
    xymap, counts = collections.defaultdict(int), collections.Counter()
    sizes = db.fetch("screen_sizes", order=("dt",))
    sizeidx, sizelen = -1, len(sizes) # Scale by desktop size at event time
    for e in events:
        e["dt"] = datetime.datetime.fromtimestamp(e["stamp"])
        if not first: first = e
        if last:
            totaldelta += e["dt"] - last["dt"]
            distance += math.sqrt(sum(abs(e[k] - last[k])**2 for k in "xy"))
        last = dict(e) # Copy as we modify coordinates
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
                SC = dict((k, sizes[sizeidx][k] / float(HS["y" == k]))
                          for k in "xy")
        e["x"], e["y"] = tuple(min(int(e[k] / SC[k]), HS["y" == k]) for k in "xy")
        xymap[(e["x"], e["y"])] += 1
        if "moves" != table:
            counts.update([e["button" if "clicks" == table else "wheel"]])
            all_events.append(e)
        count += 1

    stats, positions = [], [dict(x=x, y=y, count=v) for (x, y), v in xymap.items()]
    if "moves" == table and count:
        px = re.sub(r"(\d)(?=(\d{3})+(?!\d))", r"\1,", "%d" % math.ceil(distance))
        seconds = timedelta_seconds(last["dt"] - first["dt"])
        stats = [("Total distance", "%s pixels " % px),
                 ("", "%.1f meters (if pixel is %smm)" %
                  (distance * conf.PixelLength, conf.PixelLength * 1000)),
                 ("Average speed", "%.1f pixels per second" % (distance / (seconds or 1))),
                 ("", "%.4f meters per second" %
                  (distance * conf.PixelLength / (seconds or 1))), ]
    elif "scrolls" == table and count:
        stats = [("Scrolls per hour", 
                  int(count / (timedelta_seconds(last["dt"] - first["dt"]) / 3600 or 1))),
                 ("Average interval", totaldelta / count),
                 ("Scrolls down", counts[-1]),
                 ("Scrolls up", counts[1]), ]
    elif "clicks" == table and count:
        NAMES = {1: "Left", 2: "Right", 3: "Middle"}
        stats = [("Clicks per hour", 
                  int(count / (timedelta_seconds(last["dt"] - first["dt"]) / 3600 or 1))),
                 ("Average interval between clicks", totaldelta / count),
                 ("Average distance between clicks",
                  "%.1f pixels" % (distance / count)), ]
        for k, v in sorted(counts.items()):
            stats += [("%s button clicks" % NAMES.get(k, "%s." % k), v)]
    if count:
        stats += [("Total time interval", format_timedelta(last["dt"] - first["dt"]))]
    return stats, positions, count, all_events


def timedelta_seconds(timedelta):
    """Returns the total timedelta duration in seconds."""
    return (timedelta.total_seconds() if hasattr(timedelta, "total_seconds")
            else timedelta.days * 24 * 3600 + timedelta.seconds +
                 timedelta.microseconds / 1000000.)


def format_timedelta(timedelta):
    """Formats the timedelta as "3d 40h 23min 23.1sec"."""
    dd, rem = divmod(timedelta_seconds(timedelta), 24*3600)
    hh, rem = divmod(rem, 3600)
    mm, ss  = divmod(rem, 60)
    items = []
    for c, n in (dd, "d"), (hh, "h"), (mm, "min"), (ss, "sec"):
        f = "%d" % c if "second" != n else str(c).rstrip("0").rstrip(".")
        if f != "0": items += [f + n]
    return " ".join(items or ["0 seconds"])


def init():
    """Initialize configuration and web application."""
    global app
    if app: return app
    conf.init(), db.init(conf.DbPath, conf.DbStatements)

    bottle.TEMPLATE_PATH.insert(0, conf.TemplatePath)
    app = bottle.default_app()
    bottle.BaseTemplate.defaults.update(get_url=app.get_url)
    return app


def start():
    """Starts the web server."""
    global app
    bottle.run(app, host=conf.WebHost, port=conf.WebPort,
               debug=conf.WebAutoReload, reloader=conf.WebAutoReload,
               quiet=conf.WebQuiet)

def main():
    """Entry point for stand-alone execution."""
    conf.WebQuiet = "--quiet" in sys.argv
    start()


app = init()


if "__main__" == __name__:
    main()
