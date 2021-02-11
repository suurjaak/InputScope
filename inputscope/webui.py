# -*- coding: utf-8 -*-
"""
Web frontend interface, displays statistics from a database.

--quiet      prints out nothing

@author      Erki Suurjaak
@created     06.04.2015
@modified    10.02.2021
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

    where = (("day", period), ) if period else ()
    if not period: # Mouse tables can have 100M+ rows, total order takes too long
        mydays, mycount = [], 0
        for myday in days:
            mydays, mycount = mydays + [myday["day"]], mycount + myday["count"]
            if mycount >= conf.MaxEventsForStats: break # for myday
        if len(mydays) != len(days):
            where = (("day", ("IN", mydays)), )
    elif len(period) < 8: # Month period, query by known month days
        mydays = [v["day"] for v in days if v["day"][:7] == period]
        where = (("day", ("IN", mydays)), )

    events = db.select(table, where=where, order="stamp", limit=conf.MaxEventsForStats)
    stats, positions, events = stats_mouse(events, table, count)
    dbinfo = stats_db(conf.DbPath)
    return bottle.template("heatmap_mouse.tpl", locals(), conf=conf)


@route("/keyboard/<table>")
@route("/keyboard/<table>/<period>")
def keyboard(table, period=None):
    """Handler for showing the keyboard statistics page."""
    days, input = db.fetch("counts", order="day", type=table), "keyboard"
    if period and not any(v["day"][:len(period)] == period for v in days):
        return bottle.redirect(request.app.get_url("/<input>", input=input))

    count = sum(v["count"] for v in days if not period or v["day"][:len(period)] == period)
    tabledays = set(x["type"] for x in db.fetch("counts", day=("LIKE", period + "%"))) if period else {}

    where = (("day", period), ) if period else ()
    if period and len(period) < 8: # Month period, query by known month days
        mydays = [v["day"] for v in days if v["day"][:7] == period]
        where = (("day", ("IN", mydays)), )
    cols, group = "realkey AS key, COUNT(*) AS count", "realkey"
    counts_display = counts = db.fetch(table, cols, where, group, "count DESC")
    if "combos" == table:
        counts_display = db.fetch(table, "key, COUNT(*) AS count", where,
                                  "key", "count DESC")

    events = db.select(table, where=where, order="stamp", limit=conf.MaxEventsForStats)
    stats, events = stats_keyboard(events, table, count)
    dbinfo = stats_db(conf.DbPath)
    return bottle.template("heatmap_keyboard.tpl", locals(), conf=conf)


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
    ] if deltas and "combos" == table else [
        ("Keys per hour",
         int(3600 * count / timedelta_seconds(last["dt"] - first["dt"]))
         if last["dt"] != first["dt"] else count),
        ("Average key interval",
         format_timedelta(sum(deltas, datetime.timedelta()) / len(deltas))),
        ("Typing sessions (key interval < %ss)" % UNBROKEN_DELTA.seconds,
         len(sessions)),
        ("Average keys in session",
         sum(len(x) + 1 for x in sessions) / len(sessions) if sessions else 0),
        ("Average session duration", format_timedelta(sum((sum(x, datetime.timedelta())
         for x in sessions), datetime.timedelta()) / (len(sessions) or 1))),
        ("Longest session duration",
         format_timedelta(sum(longest_session, datetime.timedelta()))),
        ("Keys in longest session",
         len(longest_session) + 1),
        ("Most keys in session",
         max(len(x) + 1 for x in sessions) if sessions else 0),
    ] if deltas and "keys" == table else []
    if deltas:
        stats += [("Total time interval", format_timedelta(last["dt"] - first["dt"]))]
    return stats, collated[:conf.MaxEventsForReplay]



def stats_mouse(events, table, count):
    """Returns (statistics, positions, max-limited events)."""
    first, last, totaldelta = None, None, datetime.timedelta()
    all_events = []
    HS = conf.MouseHeatmapSize
    SZ = dict((k + 2, conf.DefaultScreenSize[k] / float(HS[k])) for k in [0, 1])
    SZ.update({"dt": datetime.datetime.min, 0: 0, 1: 0}) # {0,1,2,3: x,y,w,h}
    displayxymap  = collections.defaultdict(lambda: collections.defaultdict(int))
    counts, lasts = collections.Counter(), {} # {display: last event}
    distances     = collections.defaultdict(int)
    SIZES = {} # Scale by desktop size at event time; {display: [{size}, ]}
    for row in db.fetch("screen_sizes", order=("dt",)):
        row.update({0: row["x"], 2: row["w"] / float(HS[0]),
                    1: row["y"], 3: row["h"] / float(HS[1])})
        SIZES.setdefault(row["display"], []).append(row)
    cursizes = {k: None for k in SIZES}
    for e in events:
        e["dt"] = datetime.datetime.fromtimestamp(e.pop("stamp"))
        if not first: first = e
        if e["display"] in lasts:
            mylast = lasts[e["display"]]
            totaldelta += e["dt"] - mylast["dt"]
            distances[e["display"]] += math.sqrt(sum(abs(e[k] - mylast[k])**2 for k in "xy"))
        last = lasts[e["display"]] = dict(e) # Copy, as we modify coordinates for heatmap

        sz, sizes = cursizes.get(e["display"]), SIZES.get(e["display"], [SZ])
        if not sz or sz["dt"] > e["dt"]:
            # Find latest size from before event, fallback to first size recorded
            sz = next((s for s in sizes[::-1] if e["dt"] >= s["dt"]), sizes[0])
            cursizes[e["display"]] = sz

        # Make heatmap coordinates, scaling event to screen size at event time
        e["x"], e["y"] = [int((e["xy"[k]] - sz[k]) / sz[k + 2]) for k in [0, 1]]
        # Constraint within heatmap, events at edges can have off-screen coordinates
        e["x"], e["y"] = [max(0, min(e["xy"[k]], HS[k])) for k in [0, 1]]
        displayxymap[e["display"]][(e["x"], e["y"])] += 1
        if "clicks" == table: counts.update(str(e["button"]))
        elif "scrolls" == table: counts.update({
            ("-" if e[k] < 0 else "") + k: bool(e[k]) for k in ("dx", "dy")
        })
        if len(all_events) < conf.MaxEventsForReplay:
            for k in ("id", "day", "button", "dx", "dy"): e.pop(k, None)
            all_events.append(e)

    positions = {i: [dict(x=x, y=y, count=v) for (x, y), v in displayxymap[i].items()]
                 for i in sorted(displayxymap)}
    stats, distance = [], sum(distances.values())
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
        stats = filter(bool, [("Scrolls per hour", 
                  int(count / (timedelta_seconds(last["dt"] - first["dt"]) / 3600 or 1))),
                 ("Average interval", totaldelta / (count or 1)),
                 ("Scrolls down",  counts["-dy"]),
                 ("Scrolls up",    counts["dy"]), 
                 ("Scrolls left",  counts["dx"])  if counts["dx"]  else None, 
                 ("Scrolls right", counts["-dx"]) if counts["-dx"] else None, ])
    elif "clicks" == table and count:
        NAMES = {"1": "Left", "2": "Right", "3": "Middle"}
        stats = [("Clicks per hour", 
                  int(count / (timedelta_seconds(last["dt"] - first["dt"]) / 3600 or 1))),
                 ("Average interval between clicks", totaldelta / (count or 1)),
                 ("Average distance between clicks",
                  "%.1f pixels" % (distance / (count or 1))), ]
        for k, v in sorted(counts.items()):
            stats += [("%s button clicks" % NAMES.get(k, "%s." % k), v)]
    if count:
        stats += [("Total time interval", format_timedelta(last["dt"] - first["dt"]))]
    return stats, positions, all_events


def stats_db(filename):
    """Returns database information as [(label, value), ]."""
    result = [("Database", filename),
              ("Created", datetime.datetime.fromtimestamp(os.path.getctime(filename))),
              ("Last modified", datetime.datetime.fromtimestamp(os.path.getmtime(filename))),
              ("Size", format_bytes(os.path.getsize(filename))), ]
    counts = db.fetch("counts", "type, SUM(count) AS count", group="type")
    cmap = dict((x["type"], x["count"]) for x in counts)
    for name, tables in conf.InputTables:
        countstr = "{:,}".format(sum(cmap.get(t) or 0 for t in tables))
        result += [("%s events" % name.capitalize(), countstr)]
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
    try: db.execute("PRAGMA journal_mode = WAL")
    except Exception: pass

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
