# -*- coding: utf-8 -*-
"""
Web frontend interface, displays statistics from a database.

--quiet      prints out nothing

------------------------------------------------------------------------------
This file is part of InputScope - mouse and keyboard input visualizer.
Released under the MIT License.

@author      Erki Suurjaak
@created     06.04.2015
@modified    15.04.2024
------------------------------------------------------------------------------
"""
import collections
import datetime
import io
import math
import os
import re
import sys
import time
try:  # Workaround for Py3 bug in W7: sys.stdout and .stderr are set to None
      # when using pythonw.exe, but bottle expects output streams to exist.
    _stdout, _stderr = sys.stdout, sys.stderr
    if sys.stdout is None: sys.stdout = io.StringIO()
    if sys.stderr is None: sys.stderr = io.StringIO()
    import bottle
finally:
    sys.stdout, sys.stderr = _stdout, _stderr
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
@route("/<input>/<table>/app/<appnames:path>")
@route("/<input>/<table>/app/id\:<appids>") # Colon in URL needs escaping for Bottle
@route("/<input>/<table>/<period>")
@route("/<input>/<table>/<period>/app/<appnames:path>")
@route("/<input>/<table>/<period>/app/id\:<appids>")
@route("/sessions/<session>/<input>/<table>")
@route("/sessions/<session>/<input>/<table>/app/<appnames:path>")
@route("/sessions/<session>/<input>/<table>/app/id\:<appids>")
@route("/sessions/<session>/<input>/<table>/<period>")
@route("/sessions/<session>/<input>/<table>/<period>/app/<appnames:path>")
@route("/sessions/<session>/<input>/<table>/<period>/app/id\:<appids>")
def inputdetail(input, table, period=None, session=None, appids=None, appnames=None):
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

    apps = db.fetch("programs", order="LOWER(path)") if conf.ProgramsEnabled else []
    app_ids, app_search = None, appnames
    if conf.ProgramsEnabled and appids:
        appids = [int(x) for x in (x.strip() for x in appids.split(",")) if x.isdigit()]
        app_ids = [x["id"] for x in apps if x["id"] in appids]
        appnames = app_search = ""
    elif conf.ProgramsEnabled and appnames:
        appnames = [a or b for a, b in re.findall(r'"([^"]+)"|(\S+)', appnames.lower())]
        app_ids = [x["id"] for x in apps if any(y in x["path"].lower() for y in appnames)]
    if app_ids is not None:
        app_ids.sort()
        where += [("fk_program", ("IN", app_ids))]

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
    elif period and len(period) < 8: # Month/year period, query by known period days
        mydays = [v["day"] for v in days if v["day"][:len(period)] == period]
        where += [("day", ("IN", mydays))]
    elif period:
        where += [("day", period)]

    if app_ids is not None:
        count = db.fetchone(table, "COUNT(*) AS count", where=where)["count"]
    events = db.select(table, where=where, order="stamp", limit=conf.MaxEventsForStats)
    if "mouse" == input:
        stats_texts, app_stats, heatmap_sizes, heatmap_stats, events = stats_mouse(events, table, count)
    else:
        stats_texts, app_stats, events = stats_keyboard(events, table, count)
        heatmap_stats = db.fetch(table, "realkey AS key, COUNT(*) AS count", where, "realkey", "count DESC")
        key_stats = heatmap_stats if "keys" == table else \
                    db.fetch(table, "key, COUNT(*) AS count", where, "key", "count DESC")

    if app_ids is not None and len(apps) - len(app_stats): # Populate totals for apps outside filter
        appmap = {x["id"]: x for x in apps}
        where2 = [(k, v) for k, v in where if k != "fk_program"]
        where2 += [("fk_program", ("NOT IN", app_stats))]
        for row in db.fetch(table, "fk_program, COUNT(*) AS count", where=where2, group="fk_program"):
            app_stats[row["fk_program"]] = {"path": appmap.get(row["fk_program"], {}).get("path"),
                                            "total": row["count"]}

    dbinfo, session = stats_db(conf.DbPath), sess
    return bottle.template("heatmap.tpl", locals(), conf=conf)


@route("/<input>")
def inputindex(input):
    """Handler for showing keyboard or mouse page with day and total links."""
    if input not in conf.InputEvents:
        return bottle.redirect(request.app.get_url("/"))
    stats = {} # {category: {count, first, last, periods}}
    countminmax = "SUM(count) AS count, MIN(day) AS first, MAX(day) AS last"
    for table in conf.InputEvents[input]:
        stats[table] = db.fetchone("counts", countminmax, type=table)
        periods, month, year, months = [], None, None, 0
        for data in db.fetch("counts", "day AS period, count, 'day' AS class", order="day DESC", type=table):
            if not month or month["period"][:4] != data["period"][:4]:
                year = {"class": "year", "period": data["period"][:4], "count": 0}
                periods.append(year)
            if not month or month["period"][:7] != data["period"][:7]:
                month = {"class": "month", "period": data["period"][:7], "count": 0}
                periods.append(month)
                months += 1
            month["count"] += data["count"]
            year["count"] += data["count"]
            periods.append(data)
        if months < 2: periods = [x for x in periods if "year" != x["class"]]
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
    """Return (statistics, app statistics, collated and max-limited events) for keyboard events."""
    KEYNAME = "realkey" if "keys" == table else "key"
    appmap = {x["id"]: x["path"] for x in db.select("programs")} if conf.ProgramsEnabled else {}
    app_stats = {}  # {id: Counter(key: count)}
    deltas, first, last = [], None, None
    tsessions, tsession = [], None
    UNBROKEN_DELTA = datetime.timedelta(seconds=conf.KeyboardSessionMaxDelta)
    blank = collections.defaultdict(lambda: collections.defaultdict(int))
    collated = [blank.copy()] # [{dt, keys: {key: count}}]
    uniques = set()
    for e in events:
        e.pop("id") # Decrease memory overhead
        e["dt"] = datetime.datetime.fromtimestamp(e.pop("stamp"))
        if not first: first = e
        app_id = e.pop("fk_program")
        if not app_id or app_id in appmap:
            app_stats.setdefault(app_id, collections.Counter()).update([e[KEYNAME]])
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
        uniques.add(e["key"])
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
    stats += [("Total unique %s" % table, len(uniques))]
    if deltas:
        stats += [("Total time interval", format_timedelta(last["dt"] - first["dt"]))]
    app_items = [{"id": k, "cols": {"top": [a for a, _ in v.most_common(conf.KeyboardTopForPrograms)]},
                  "path": appmap.get(k), "total": sum(v.values())} for k, v in app_stats.items()]
    app_results = collections.OrderedDict(
        (x["id"], x) for x in sorted(app_items, key=lambda x: x["total"], reverse=True)
    )
    return stats, app_results, collated[:conf.MaxEventsForReplay]


def stats_mouse(events, table, count):
    """Returns (statistics, app statistics, positions, max-limited events)."""
    BUTTON_NAMES = collections.OrderedDict([("1", "Left"), ("2", "Right"), ("3", "Middle")])
    SCROLL_NAMES = collections.OrderedDict([("dy", "down"), ("-dy", "up"),
                                            ("-dx", "left"), ("dx", "right")])
    appmap = {x["id"]: x["path"] for x in db.select("programs")} if conf.ProgramsEnabled else {}
    app_stats = {}  # {id: Counter(button: count)}
    first, last, totaldelta = None, None, datetime.timedelta()
    all_events = []
    HS = conf.MouseHeatmapSize
    SZ = {0: 0, 1: 0, "dt": datetime.datetime.min} # {0,1,2,3,dt: xmin,ymin,w,h,startdt}
    SZ.update((k + 2, conf.DefaultScreenSize[k]) for k in [0, 1])
    displayxymap  = collections.defaultdict(lambda: collections.defaultdict(int))
    counts, distances = collections.Counter(), collections.defaultdict(float)
    app_deltas = collections.defaultdict(datetime.timedelta) # {id: time in app}
    app_distances = collections.defaultdict(float) # {id: pixels}
    SIZES = {} # Desktop sizes for event times, as {display: [{0,1,2,3,dt}, ]}
    vals = lambda d, kk="xywh": [d[k] for k in kk]
    for row in db.fetch("screen_sizes", order="dt"):
        row.update({0: row["x"], 1: row["y"], 2: row["w"], 3: row["h"]})
        if row["display"] not in SIZES or vals(SIZES[row["display"]][-1]) != vals(row):
            SIZES.setdefault(row["display"], []).append(row)
    cursizes = {k: None for k in SIZES} # {display: {0,1,2,3,dt}}
    heatmap_sizes = {} # {display: (w, h)} scaled to screen size of first event
    for e in events:
        e["dt"] = datetime.datetime.fromtimestamp(e.pop("stamp"))
        if not first: first = e
        app_id = e["fk_program"]
        if not app_id or app_id in appmap: app_stats.setdefault(app_id, collections.Counter())
        if last and last["display"] == e["display"]:
            totaldelta += e["dt"] - last["dt"]
            distances[e["display"]] += math.sqrt(sum(abs(e[k] - last[k])**2 for k in "xy"))
            if appmap and last["fk_program"] == e["fk_program"]:
                app_deltas[app_id] += e["dt"] - last["dt"]
                app_distances[app_id] += math.sqrt(sum(abs(e[k] - last[k])**2 for k in "xy"))
        last = dict(e) # Copy, as we modify coordinates for heatmap

        sz, sizes = cursizes.get(e["display"]), SIZES.get(e["display"], [SZ])
        if not sz or sz["dt"] > e["dt"]:
            # Find latest size from before event, fallback to first size recorded
            sz = next((s for s in sizes[::-1] if e["dt"] >= s["dt"]), sizes[0])
            cursizes[e["display"]] = sz
        if e["display"] not in heatmap_sizes: # Make heatmap scaled to screen height
            heatmap_sizes[e["display"]] = (HS[0], HS[0] * sz["h"] / sz["w"])
        hs = heatmap_sizes[e["display"]]

        # Make heatmap coordinates, scaling event to screen size at event time
        e["x"], e["y"] = [int(float(e["xy"[k]] - sz[k]) * hs[k] / sz[k + 2]) for k in [0, 1]]
        # Constrain within heatmap, events at edges can have off-screen coordinates
        e["x"], e["y"] = [max(0, min(e["xy"[k]], hs[k])) for k in [0, 1]]
        displayxymap[e["display"]][(e["x"], e["y"])] += 1
        if "moves" == table:
            if appmap: app_stats[app_id].update([table])
        elif "clicks" == table:
            counts.update(str(e["button"]))
            if appmap: app_stats[app_id].update([str(e["button"])])
        elif "scrolls" == table:
            for k in ("dx", "dy"):
                key, value = "%s%s" % ("-" if e[k] < 0 else "", k), abs(e[k])
                counts[key] += value
                if appmap: app_stats[app_id][key] += value
        if len(all_events) < conf.MaxEventsForReplay:
            for k in ("id", "day", "button", "dx", "dy", "fk_program"): e.pop(k, None)
            all_events.append(e)

    positions = {i: [dict(x=x, y=y, count=v) for (x, y), v in displayxymap[i].items()]
                 for i in sorted(displayxymap)}
    stats, distance = [], sum(distances.values())
    app_items = []
    if "moves" == table and count:
        px = re.sub(r"(\d)(?=(\d{3})+(?!\d))", r"\1,", "%d" % math.ceil(distance))
        seconds = timedelta_seconds(last["dt"] - first["dt"])
        stats = [("Total distance", "%s pixels " % px),
                 ("", "%.1f meters (if pixel is %smm)" %
                  (distance * conf.PixelLength, conf.PixelLength * 1000)),
                 ("Average speed", "%.1f pixels per second" % (distance / (seconds or 1))),
                 ("", "%.4f meters per second" %
                  (distance * conf.PixelLength / (seconds or 1))), ]
        app_items = [{"id": k, "path": appmap.get(k), "total": sum(v.values()),
                      "cols": collections.OrderedDict([
                          ("pixels", re.sub(r"(\d)(?=(\d{3})+(?!\d))", r"\1,", "%d px" % d)),
                          ("meters", re.sub(r"(\d)(?=(\d{3})+(?!\d))", r"\1,", "%.1f m" %
                                     (d * conf.PixelLength))),
                          ("time", format_timedelta(app_deltas[k])),
                     ])} for k, v in app_stats.items() for d in [math.ceil(app_distances[k])]]
    elif "scrolls" == table and count:
        stats = list(filter(bool, [("Scrolls per hour", 
                  int(count / (timedelta_seconds(last["dt"] - first["dt"]) / 3600 or 1))),
                 ("Average interval", format_timedelta(totaldelta / (count or 1))),
                 ] + [("Scrolls %s" % SCROLL_NAMES[k], counts[k])
                      for k in SCROLL_NAMES if "dy" in k or counts[k]]))
        app_items = [{"id": k, "path": appmap.get(k), "total": sum(v.values()),
                      "cols": collections.OrderedDict((b, v[a]) for a, b in SCROLL_NAMES.items()
                                                      if v.get(a))}
                       for k, v in app_stats.items()]
    elif "clicks" == table and count:
        stats = [("Clicks per hour", 
                  int(count / (timedelta_seconds(last["dt"] - first["dt"]) / 3600 or 1))),
                 ("Average interval between clicks", format_timedelta(totaldelta / (count or 1))),
                 ("Average distance between clicks",
                  "%.1f pixels" % (distance / (count or 1))), ]
        for k, v in sorted(counts.items()):
            stats += [("%s button clicks" % BUTTON_NAMES.get(k, "%s." % k), v)]
        app_items = [{"id": k, "path": appmap.get(k), "total": sum(v.values()),
                      "cols": collections.OrderedDict((b, v[a]) for a, b in BUTTON_NAMES.items()
                                                      if v.get(a))}
                       for k, v in app_stats.items()]
    if count:
        stats += [("Total time interval", format_timedelta(last["dt"] - first["dt"]))]
    app_results = collections.OrderedDict(
        (x["id"], x) for x in sorted(app_items, key=lambda x: x["total"], reverse=True)
    )
    return stats, app_results, heatmap_sizes, positions, all_events


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
              ("Size", format_bytes(db.get_size(filename))), ]
    counts = db.fetch("counts", "type, SUM(count) AS count", group="type")
    cmap = dict((x["type"], x["count"]) for x in counts)
    for name, tables in conf.InputTables:
        countstr = "{:,}".format(sum(cmap.get(t) or 0 for t in tables))
        result += [("%s events" % name.capitalize(), countstr)]
    result += [("Sessions", db.fetchone("sessions", "COUNT(*) AS count")["count"])]
    result += [("%s version" % conf.Title, "%s (%s)" % (conf.Version, conf.VersionDate))]
    result += [("Configuration", conf.ConfigPath or "")]
    return result


def make_url(**kwargs):
    """Returns new URL from current URL, modified with added or cleared keyword arguments."""
    ARGORDER = collections.OrderedDict([
        ("session",  "/sessions/<session>"),  ("input",  "/<input>"),
        ("table",    "/<table>"),             ("period", "/<period>"),
        ("appnames", "/app/<appnames:path>"), ("appids", "/app/id\:<appids>"),
    ])
    rule, ruleargs = request.route.rule, dict(request.url_args)
    for k, v in ((k, kwargs[k]) for k in ARGORDER if k in kwargs):
        if v is None: # Remove arg from route
            rule = rule.replace(ARGORDER[k], "")
            ruleargs.pop(k, None)
        elif k not in ruleargs: # Add arg to route
            pos, prev = 0, None
            for arg in ARGORDER:
                if arg == k:
                    if prev: pos = rule.index(prev) + len(prev)
                    break # for arg
                elif arg in ruleargs: prev = ARGORDER[arg]
            rule = rule[:pos] + ARGORDER[k] + rule[pos:]
            ruleargs[k] = v
        else: ruleargs[k] = v
    return app.get_url(rule, **ruleargs)


def init():
    """Initialize configuration and web application."""
    global app
    if app: return app
    conf.init(), db.init(conf.DbPath, conf.DbStatements)
    try: db.execute("PRAGMA journal_mode = WAL")
    except Exception: pass

    bottle.TEMPLATE_PATH.insert(0, conf.TemplatePath)
    app = bottle.default_app()
    bottle.BaseTemplate.defaults.update(get_url=app.get_url, make_url=make_url)
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
