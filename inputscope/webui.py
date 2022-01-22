# -*- coding: utf-8 -*-
"""
Web frontend interface, displays statistics from a database.

--quiet      prints out nothing

@author      Erki Suurjaak
@created     06.04.2015
@modified    19.10.2021
"""
import collections
import datetime
import math
import os
import re
import sys
import time
import bottle
from bottle import hook, request, route

from . import conf
from . import db
from . util import format_bytes, format_stamp, format_timedelta, stamp_to_date, timedelta_seconds


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


@route("/sessions/<session>")
def session(session):
    """Handler for showing the GUI index page."""
    sess = db.fetchone("sessions", id=session)
    if not sess:
        return bottle.redirect(request.app.get_url("/"))

    stats = {} # {category: {count, first, last, periods}}
    COLS = "COUNT(*) as count, day AS period, 'day' AS class"
    where = [("day", (">=", stamp_to_date(sess["start"]))),
             ("stamp", (">=", sess["start"]))]
    if sess["end"]: where += [("day", ("<=", stamp_to_date(sess["end"]))),
                              ("stamp", ("<", sess["end"] or time.time()))]
    for table in (t for _, tt in conf.InputTables for t in tt):
        stats[table] = {"count": 0, "periods": []}
        for row in db.fetch(table, COLS, where=where, group="day"):
            stats[table]["count"]   += row["count"]
            stats[table]["periods"] += [row]

    dbinfo, sessioninfo, session = stats_db(conf.DbPath), stats_session(sess, stats), sess
    return bottle.template("session.tpl", locals(), conf=conf)


@route("/sessions/<session>/<input>")
def inputsessionindex(session, input):
    """Handler for showing keyboard or mouse page with day and total links."""
    sess = db.fetchone("sessions", id=session)
    if not sess:
        return bottle.redirect(request.app.get_url("/<input>", input=input))

    stats = {} # {category: {count, first, last, periods}}
    countminmax = "COUNT(*) AS count, MIN(day) AS first, MAX(day) AS last"
    where = [("day", (">=", stamp_to_date(sess["start"]))),
             ("stamp", (">=", sess["start"]))]
    if sess["end"]: where += [("day", ("<=", stamp_to_date(sess["end"]))),
                              ("stamp", ("<", sess["end"]))]
    for table in conf.InputEvents[input]:
        stats[table] = db.fetchone(table, "COUNT(*) AS count, MIN(day) AS first, MAX(day) AS last",
                                   where=where)
        stats[table]["periods"] = db.fetch(table, "day AS period, COUNT(*) AS count, 'day' AS class",
                                           where=where, group="day", order="day DESC")

    dbinfo, session, sessions = stats_db(conf.DbPath), sess, []
    return bottle.template("input.tpl", locals(), conf=conf)


@route("/<input>/<table>")
@route("/<input>/<table>/<period>")
@route("/sessions/<session>/<input>/<table>")
@route("/sessions/<session>/<input>/<table>/<period>")
def inputdetail(input, table, period=None, session=None):
    """Handler for showing mouse/keyboard statistics page."""
    sess = db.fetchone("sessions", id=session) if session else None
    if session and not sess:
        url, kws = "/<input>/<table>", dict(input=input, table=table)
        if period: url, kws = (url + "/<period>", dict(kws, period=period))
        return bottle.redirect(request.app.get_url(url, **kws))

    where = [("day", (">=", stamp_to_date(sess["start"])))] if sess else []
    if sess and sess["end"]: where += [("day", ("<=", stamp_to_date(sess["end"])))]
    days = db.fetch("counts", order="day", where=where, type=table)
    if period and not any(v["day"][:len(period)] == period for v in days):
        url, kws = "/<input>", dict(input=input)
        if session: url, kws = ("/sessions/<session>" + url, dict(kws, session=session))
        return bottle.redirect(request.app.get_url(url, **kws))

    if sess:
        where += [("stamp", (">=", sess["start"]))]
        if sess["end"]: where += [("stamp", ("<", sess["end"]))]
        days = db.fetch(table, "day || '' AS day, COUNT(*) AS count", where=where, group="day", order="day")
        where2 = where + ([("day", ("LIKE", period + "%"))] if period else [])
        count = db.fetchone(table, "COUNT(*) AS count", where=where2)["count"]
        tabledays = set(t for _, tt in conf.InputTables for t in tt
                        if t != table and db.fetchone(t, "1", where=where2))
    else:
        count = sum(v["count"] for v in days if not period or v["day"][:len(period)] == period)
        tabledays = set(x["type"] for x in db.fetch("counts", day=("LIKE", period + "%"))) if period else {}

    if not period and "mouse" == input: # Mouse tables can have 100M+ rows, total order takes too long
        mydays, mycount = [], 0
        for myday in days:
            mydays, mycount = mydays + [myday["day"]], mycount + myday["count"]
            if mycount >= conf.MaxEventsForStats: break # for myday
        if len(mydays) != len(days):
            where += [("day", ("IN", mydays))]
    elif period and len(period) < 8: # Month period, query by known month days
        mydays = [v["day"] for v in days if v["day"][:7] == period]
        where += [("day", ("IN", mydays))]
    elif period:
        where += [("day", period)]
    if "keyboard" == input:
        cols, group = "realkey AS key, COUNT(*) AS count", "realkey"
        counts_display = counts = db.fetch(table, cols, where, group, "count DESC")
        if "combos" == table:
            counts_display = db.fetch(table, "key, COUNT(*) AS count", where,
                                      "key", "count DESC")

    events = db.select(table, where=where, order="stamp", limit=conf.MaxEventsForStats)
    if "mouse" == input:
        stats, positions, events = stats_mouse(events, table, count)
    else:
        stats, events = stats_keyboard(events, table, count)
    dbinfo, session = stats_db(conf.DbPath), sess
    template = "heatmap_mouse.tpl" if "mouse" == input else "heatmap_keyboard.tpl"
    return bottle.template(template, locals(), conf=conf)


@route("/<input>")
def inputindex(input):
    """Handler for showing keyboard or mouse page with day and total links."""
    if input not in conf.InputEvents:
        return bottle.redirect(request.app.get_url("/"))
    stats = {} # {category: {count, first, last, periods}}
    countminmax = "SUM(count) AS count, MIN(day) AS first, MAX(day) AS last"
    for table in conf.InputEvents[input]:
        stats[table] = db.fetchone("counts", countminmax, type=table)
        periods, month = [], None
        for data in db.fetch("counts", "day AS period, count, 'day' AS class", order="day DESC", type=table):
            if not month or month["period"][:7] != data["period"][:7]:
                month = {"class": "month", "period": data["period"][:7], "count": 0}
                periods.append(month)
            month["count"] += data["count"]
            periods.append(data)
        stats[table]["periods"] = periods
    dbinfo, sessions = stats_db(conf.DbPath), stats_sessions(input=input)
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
    dbinfo, sessions = stats_db(conf.DbPath), stats_sessions()
    return bottle.template("index.tpl", locals(), conf=conf)


def stats_keyboard(events, table, count):
    """Return (statistics, collated and max-limited events) for keyboard events."""
    deltas, first, last = [], None, None
    tsessions, tsession = [], None
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
                tsession = None
            else:
                if not tsession:
                    tsession = []
                    tsessions.append(tsession)
                tsession.append(delta)
        collated[-1]["dt"] = e["dt"]
        collated[-1]["keys"][e["realkey"]] += 1
        last = e

    longest_session = max(tsessions + [[datetime.timedelta()]], key=lambda x: sum(x, datetime.timedelta()))
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
         len(tsessions)),
        ("Average keys in session",
         int(round(sum(len(x) + 1 for x in tsessions) / len(tsessions))) if tsessions else 0),
        ("Average session duration", format_timedelta(sum((sum(x, datetime.timedelta())
         for x in tsessions), datetime.timedelta()) / (len(tsessions) or 1))),
        ("Longest session duration",
         format_timedelta(sum(longest_session, datetime.timedelta()))),
        ("Keys in longest session",
         len(longest_session) + 1),
        ("Most keys in session",
         max(len(x) + 1 for x in tsessions) if tsessions else 0),
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
    for row in db.fetch("screen_sizes", order="dt"):
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
            ("-" if e[k] < 0 else "") + k: abs(e[k]) for k in ("dx", "dy")
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
        stats = list(filter(bool, [("Scrolls per hour", 
                  int(count / (timedelta_seconds(last["dt"] - first["dt"]) / 3600 or 1))),
                 ("Average interval", totaldelta / (count or 1)),
                 ("Scrolls down",  counts["-dy"]),
                 ("Scrolls up",    counts["dy"]), 
                 ("Scrolls left",  counts["dx"])  if counts["dx"]  else None, 
                 ("Scrolls right", counts["-dx"]) if counts["-dx"] else None, ]))
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


def stats_sessions(input=None):
    """Returns a list of sessions with total event counts."""
    sessions = db.fetch("sessions", order="start DESC")
    for sess in sessions:
        sess["count"] = 0
        where = [("day", (">=", sess["day1"]))]
        if sess["end"]:
            where += [("day", ("<=", sess["day1"])), ("stamp", ("<", sess["end"]))]
        where += [("stamp", (">=", sess["start"]))]
        for table in (t for k, tt in conf.InputTables if input in (None, k) for t in tt):
            sess["count"] += db.fetchone(table, "COUNT(*) AS count", where)["count"]
    return sessions


def stats_session(session, stats):
    """Returns session information as [(label, value), ]."""
    FMT = "%Y-%m-%d %H:%M:%S"
    result = [("Started",  format_stamp(session["start"], FMT)),
              ("Ended",    format_stamp(session["end"],   FMT) if session["end"] else ""),
              ("Duration", format_timedelta((session["end"] or time.time()) - session["start"])),
              ("Mouse",    "{:,}".format(sum(stats.get(t, {}).get("count", 0) for t in conf.InputEvents["mouse"]))),
              ("Keyboard", "{:,}".format(sum(stats.get(t, {}).get("count", 0) for t in conf.InputEvents["keyboard"]))),
              ("Total",    "{:,}".format(sum(stats.get(t, {}).get("count", 0) for _, tt in conf.InputTables for t in tt))), ]
    return result


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
    result += [("Sessions", db.fetchone("sessions", "COUNT(*) AS count")["count"])]
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
