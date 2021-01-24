# -*- coding: utf-8 -*-
"""
Web frontend interface, displays statistics from a database.

--quiet      prints out nothing

@author      Erki Suurjaak
@created     06.04.2015
@modified    23.01.2021
"""
import collections
import datetime
import math
import os
import re
import sys
import bottle
from bottle import hook, request, route

import conf
import db

app = None   # Bottle application instance


@hook("before_request")
def before_request():
    """Remove trailing slashes from route."""
    request.environ["PATH_INFO"] = request.environ["PATH_INFO"].rstrip("/")


@route("/static/<filepath:path>")
def server_static(filepath):
    """Handler for serving static files."""
    mimetype = "image/svg+xml" if filepath.endswith(".svg") else "auto"
    return bottle.static_file(filepath, root=conf.StaticPath, mimetype=mimetype)


@route("/mouse/<table>")
@route("/mouse/<table>/<period>")
def mouse(table, period=None):
    """Handler for showing mouse statistics for specified type and day."""
    days, input = db.fetch("counts", order="day", type=table), "mouse"
    if period and not any(v["day"][:len(period)] == period for v in days):
        return bottle.redirect(request.app.get_url("/<input>", input=input))
        
    count = sum(v["count"] for v in days if not period or v["day"][:len(period)] == period)
    tabledays = set(x["type"] for x in db.fetch("counts", day=("LIKE", period + "%"))) if period else {}

    where = (("day", ("LIKE", period + "%")), ) if period else ()
    if not period: # Mouse tables can have 100M+ rows, total order takes too long
        mydays, mycount = [], 0
        for myday in days:
            mydays, mycount = mydays + [myday["day"]], mycount + myday["count"]
            if mycount >= conf.MaxEventsForStats: break # for myday
        if len(mydays) != len(days):
            where = (("day", ("IN", mydays)), )
    events = db.select(table, where=where, order="stamp", limit=conf.MaxEventsForStats)
    stats, positions, events = stats_mouse(events, table, count)
    dbinfo = stats_db(conf.DbPath)
    return bottle.template("heatmap.tpl", locals(), conf=conf)


@route("/keyboard/<table>")
@route("/keyboard/<table>/<period>")
def keyboard(table, period=None):
    """Handler for showing the keyboard statistics page."""
    days, input = db.fetch("counts", order="day", type=table), "keyboard"
    if period and not any(v["day"][:len(period)] == period for v in days):
        return bottle.redirect(request.app.get_url("/<input>", input=input))

    count = sum(v["count"] for v in days if not period or v["day"][:len(period)] == period)
    tabledays = set(x["type"] for x in db.fetch("counts", day=("LIKE", period + "%"))) if period else {}

    where = (("day", ("LIKE", period + "%")), ) if period else ()
    cols, group = "realkey AS key, COUNT(*) AS count", "realkey"
    counts_display = counts = db.fetch(table, cols, where, group, "count DESC")
    if "combos" == table:
        counts_display = db.fetch(table, "key, COUNT(*) AS count", where,
                                  "key", "count DESC")

    events = db.select(table, where=where, order="stamp", limit=conf.MaxEventsForStats)
    stats, events = stats_keyboard(events, table, count)
    dbinfo = stats_db(conf.DbPath)
    return bottle.template("heatmap.tpl", locals(), conf=conf)


@route("/<input>")
def inputindex(input):
    """Handler for showing keyboard or mouse page with day and total links."""
    stats = {}
    countminmax = "SUM(count) AS count, MIN(day) AS first, MAX(day) AS last"
    tables = ("moves", "clicks", "scrolls") if "mouse" == input else ("keys", "combos")
    for table in tables:
        stats[table] = db.fetchone("counts", countminmax, type=table)
        periods, month = [], None
        for data in db.fetch("counts", "day AS period, count, 'day' AS class", order="day DESC", type=table):
            if not month or month["period"][:7] != data["period"][:7]:
                month = {"class": "month", "period": data["period"][:7], "count": 0}
                periods.append(month)
            month["count"] += data["count"]
            periods.append(data)
        stats[table]["periods"] = periods
    dbinfo = stats_db(conf.DbPath)
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
    dbinfo = stats_db(conf.DbPath)
    return bottle.template("index.tpl", locals(), conf=conf)


def stats_keyboard(events, table, count):
    """Return (statistics, collated and max-limited events) for keyboard events."""
    deltas, first, last = [], None, None
    sessions, session = [], None
    UNBROKEN_DELTA = datetime.timedelta(seconds=conf.KeyboardSessionMaxDelta)
    blank = collections.defaultdict(lambda: collections.defaultdict(int))
    collated = [blank.copy()] # [{dt, keys: {key: count}}]
    for e in events:
        e.pop("id") # Decrease memory overhead
        e["dt"] = datetime.datetime.fromtimestamp(e.pop("stamp"))
        if not first: first = e
        if last:
            if last["dt"].timetuple()[:6] != e["dt"].timetuple()[:6]: # Ignore usecs
                collated.append(blank.copy())
            delta = e["dt"] - last["dt"]
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
        last = e

    longest_session = max(sessions + [[datetime.timedelta()]], key=lambda x: sum(x, datetime.timedelta()))
    stats = [
        ("Average combo interval",
         format_timedelta(sum(deltas, datetime.timedelta()) / len(deltas))),
    ] if last and "combos" == table else [
        ("Keys per hour",
         int(3600 * count / timedelta_seconds(last["dt"] - first["dt"]))),
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
    ] if last else []
    if last:
        stats += [("Total time interval", format_timedelta(last["dt"] - first["dt"]))]
    return stats, collated[:conf.MaxEventsForReplay]



def stats_mouse(events, table, count):
    """Returns (statistics, positions, max-limited events)."""
    distance, first, last, totaldelta = 0, None, None, datetime.timedelta()
    all_events = []
    HS = conf.MouseHeatmapSize
    SC = dict(("xy"[i], conf.DefaultScreenSize[i] / float(HS[i])) for i in [0, 1])
    xymap, counts = collections.defaultdict(int), collections.Counter()
    sizes = db.fetch("screen_sizes", order=("dt",))
    sizeidx, sizelen = -1, len(sizes) # Scale by desktop size at event time
    for e in events:
        e.pop("id") # Decrease memory overhead
        e["dt"] = datetime.datetime.fromtimestamp(e.pop("stamp"))
        if not first: first = e
        if last:
            totaldelta += e["dt"] - last["dt"]
            distance += math.sqrt(sum(abs(e[k] - last[k])**2 for k in "xy"))
        last = dict(e) # Copy, as we modify coordinates for heatmap size
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
        if "moves" != table: counts.update([e["button" if "clicks" == table else "wheel"]])
        if len(all_events) < conf.MaxEventsForReplay: all_events.append(e)

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
    return stats, positions, all_events


def stats_db(filename):
    """Returns database information as [(label, value), ]."""
    conf.InputTables
    result = [("Database", filename),
              ("Created", datetime.datetime.fromtimestamp(os.path.getctime(filename))),
              ("Last modified", datetime.datetime.fromtimestamp(os.path.getmtime(filename))),
              ("Size", format_bytes(os.path.getsize(filename))), ]
    cmap = dict((x["type"], x["count"]) for x in db.fetch("counts", "type, SUM(count) AS count", group="type"))
    for name, tables in conf.InputTables:
        #total = sum(db.fetchone(t, "COUNT(*) AS c")["c"] for t in tables[:1])
        """total = 0
        for t in tables:
            print datetime.datetime.now(), t
            total += db.fetchone(t, "COUNT(*) AS c")["c"]"""
        result += [("%s events" % name.capitalize(), "{:,}".format(sum(cmap.get(t) or 0 for t in tables)))]
    return result


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


def format_bytes(size, precision=2, inter=" "):
    """Returns a formatted byte size (e.g. 421.45 MB)."""
    result = "0 bytes"
    if size:
        UNITS = [("bytes", "byte")[1 == size]] + [x + "B" for x in "KMGTPEZY"]
        exponent = min(int(math.log(size, 1024)), len(UNITS) - 1)
        result = "%.*f" % (precision, size / (1024. ** exponent))
        result += "" if precision > 0 else "."  # Do not strip integer zeroes
        result = result.rstrip("0").rstrip(".") + inter + UNITS[exponent]
    return result


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
