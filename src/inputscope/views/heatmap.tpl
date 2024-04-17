%"""
Heatmaps and statistics page for mouse and keyboard events.

Template arguments:
  input           "mouse"|"keyboard"
  table           events table to show, like "moves" or "keys"
  period          period for events, if any (day like "2020-02-20" or month like "2020-02")
  days            list of available days
  count           count of all events
  heatmap_sizes   mouse heatmap sizes scaled to screen height at first event, as {display: [w, h]}
  heatmap_stats   heatmap position counts, as {display: [{x, y, count}, ]} for mouse
                  or [{x, y, count}] for keyboard
  events          list of replayable events, as [{x, y, display, dt}] for mouse
                  or [{dt, keys: {key: count}}] for keyboard
  key_counts      keyboard event counts for heatmap, with real keys like Lshift, as [{key, count}]
  key_stats       keyboard event counts for statistics, as [{key, count}]
  session         session data, if any
  stats_texts     statistics texts, as [(label, text)]
  apps            list of all registered applications, as [{id, path}]
  app_ids         list of application IDs currently filtered by
  app_search      application filter search text
  app_stats       per-application statistics, as OrderedDict({id: {path, total, ?cols: {label: count}}})
  tabledays       set of tables that have events for specified day

------------------------------------------------------------------------------
This file is part of InputScope - mouse and keyboard input visualizer.
Released under the MIT License.

@author      Erki Suurjaak
@created     21.05.2015
@modified    13.04.2024
------------------------------------------------------------------------------
%"""
%import base64, json, os
%from inputscope import conf
%from inputscope.util import format_weekday
%WEBROOT = get_url("/")
%heatmap_sizes = heatmap_sizes if "mouse" == input else {0: conf.KeyboardHeatmapSize}
%heatmap_sizes = heatmap_sizes or {0: conf.MouseHeatmapSize}
%title = "%s %s" % (input.capitalize(), table)
%rebase("base.tpl", **locals())

<div id="tablelinks">
%for type, tbl in [(k, x) for k, tt in conf.InputTables for x in tt]:
    %if tbl == table:
  <span>{{ tbl }}</span>
    %elif tabledays and tbl not in tabledays:
  <span class="inactive">{{ tbl }}</span>
    %else:
  <a href="{{ make_url(input=type, table=tbl, period=period) }}">{{ tbl }}</a>
    %end # if tbl == table
%end # for type, tbl
</div>

<div id="heading" class="flex-row">
  <span>
    <h3>{{ title }}</h3>{{ ", %s" % period if period else "" }}
%if period:
%    try:
          <span class="weekday" title="{{ format_weekday(period, long=True) }}">{{ format_weekday(period) }}</span>
%    except Exception: pass
%    end # try
%end # if period
    ({{ "{:,}".format(count) }})
  </span>

  <span id="replaysection">
    <input type="button" id="replay_start" value="Replay" />
    <span class="range" title="Animation interval (100..1 milliseconds)">
      <label for="replay_interval" class="range_label">speed</label>
      <input type="range" id="replay_interval" min="1" max="100" value="50" />
    </span>
    <span class="range" title="Events in each step (1..100)">
      <label for="replay_step" class="range_label">step</label>
      <input type="range" id="replay_step" min="1" max="100" value="1" />
    </span>
%if count > conf.MaxEventsForReplay:
    <div id="limit">Replay limited to a maximum of {{ "{:,}".format(conf.MaxEventsForReplay) }} events.</div>
%end # if count > conf.MaxEventsForReplay
  </span>
</div>

<div id="status">
  <span id="statustext"><br /></span>
  <span id="progressbar"></span>
  <a href="javascript:;" title="Stop replay and reset heatmap" id="replay_stop">x</a>
</div>

<div class="heatmap-container" style="margin: 0 calc(-10rem + {{ (700 - max(s[0] for s in heatmap_sizes.values())) // 2 }}px - 2px);">
%for display in (heatmap_stats if heatmap_stats and "mouse" == input else [0]):
  <div class="heatmap {{ input }}" style="width: {{ heatmap_sizes[display][0] }}px; height: {{ heatmap_sizes[display][1] }}px;">
    %if "keyboard" == input:
    %    if os.path.abspath(conf.KeyboardHeatmapPath).startswith(conf.StaticPath):
    %        img_src = WEBROOT + "static/keyboard.svg"
    %    else:
    %        with open(conf.KeyboardHeatmapPath, "rb") as f:
    %            svg_raw = f.read()
    %        end # with open
    %        img_src = "data:image/svg+xml;base64," + base64.b64encode(svg_raw).decode()
    %    end # if os.path.abspath
    <img id="keyboard" src="{{ img_src }}" width="{{ heatmap_sizes[display][0] }}" height="{{ heatmap_sizes[display][1] }}" alt="" />
    %end # if "keyboard"
  </div>
  <div class="heatmap_helpers">
    %if apps:
    <a id="apps_form_show" title="Select applications">applications</a>
    %end # if apps
    <a class="fullscreen" title="Expand heatmap to full screen">full screen</a>
    %if "keyboard" == input:
    <label for="show_heatmap" class="check_label"><input type="checkbox" id="show_heatmap" checked="checked" />Show heatmap</label>
    <label for="show_keyboard" class="check_label"><input type="checkbox" id="show_keyboard" checked="checked" />Show keyboard</label>
    %end # if "keyboard"
  </div>
%end # for display

%if apps:
  <form id="apps_form" class="hidden">
  <input type="search" value="{{ app_search or "" }}" 
         placeholder="Filter applications" title="Enter words or phrases to filter applications by" />
    <div class="items"><table>
    %for item in (x for x in apps if x["id"] in app_stats):
        %is_active = app_ids and item["id"] in app_ids
        %is_hidden = app_search and not is_active
        %cls = "active" if is_active else "hidden" if is_hidden else None
      <tr{{! ' class="%s"' % cls if cls else "" }}>
        <td>
          <label title="{{ item["path"] }}">
            <input type="checkbox" value="{{ item["id"] }}"
                   {{! 'checked="checked"' if not app_search and is_active else "" }} />
          {{ item["path"] or "(unknown)" }}
          </label>
        </td>
        <td>{{ "({:,})".format(app_stats[item["id"]]["total"]) if app_stats.get(item["id"], {}).get("total") else "" }}</td>
      </tr>
    %end # for item
    </table></div>
    <input type="submit" value="Apply" />
    <input type="button" value="Clear"  id="apps_form_clear" />
    <input type="reset"  value="Cancel" />
  </form>
    %if app_ids:
  <div id="apps_current">
        %for item in (x for x in apps if x["id"] in app_ids):
    <div title="{{ item["path"] }}"{{! ' class="inactive"' if not app_stats.get(item["id"], {}).get("total") else "" }}>
      {{ os.path.split(item["path"] or "")[-1] or "(unknown)" }}
      {{ "({:,})".format(app_stats[item["id"]]["total"]) if app_stats.get(item["id"], {}).get("total") else "" }}</span>
    </div>
        %end # for item
  </div>
    %end # if app_ids
%end # if apps

</div>


<div id="tables">

%if stats_texts:
  <div class="data">
    <a title="Toggle table" class="toggle">&ndash;</a>
    <table id="stats" class="{{ input }}">
    %for key, val in stats_texts:
      <tr><td>{{ key }}</td><td>{{ val }}</td></tr>
    %end # for key, val
    %if count > conf.MaxEventsForStats:
      <tr><td colspan="2">Statistics and heatmap limited to a maximum of {{ "{:,}".format(conf.MaxEventsForStats) }} events.</td></tr>
    %end # if count > conf.MaxEventsForStats
    </table>
  </div>
%end # if stats_texts

%if "keyboard" == input:
  <div class="data">
    <a title="Toggle table" class="toggle">&ndash;</a>
    <table id="counts">
      <tr><th>Key</th><th>Count</th></tr>
    %for item in key_stats:
      <tr><td>{{ item["key"] }}</td><td>{{ item["count"] }}</td></tr>
    %end # for item
    </table>
  </div>
%end # if "keyboard"

%if len([x for x in app_stats.values() if x.get("cols")]) > 1:
%    labels = []
%    for label in (l for x in app_stats.values() for l in x.get("cols", [])):
%        labels.append(label) if label not in labels else label
%    end # for label
  <div class="data" id="app_stats">
    <a title="Toggle table" class="toggle">&ndash;</a>
    <table class="{{ input }}">
      <tr><th>Application</th>
%    for label in labels:
      <th>{{ label }}</th>
%    end # for label
      <th>Total</th></tr>
%    for item in (x for x in app_stats.values() if x.get("cols")):
      <tr>
        <td title="{{ item["path"] }}">{{ os.path.split(item["path"] or "")[-1] or "(unknown)" }}</td>
%        for label in labels:
%            v = item["cols"].get(label, "")
        <td>{{ "{:,}".format(v) if isinstance(v, int) else ", ".join(v) if isinstance(v, (list, tuple)) else v }}</td>
%        end # for label
        <td>{{ "{:,}".format(item["total"]) }}</td>
      </tr>
%    end # for item
    </table>
  </div>
%end # if len(..)

</div>

<script type="text/javascript">
<%
if "mouse" == input:
    positions = {display: [{"x": p["x"], "y": p["y"], "value": p.get("count", 1)} for p in pp]
                 for display, pp in heatmap_stats.items()}
    events = [{"x": e["x"], "y": e["y"], "display": e["display"], "dt": str(e["dt"])} for e in events]
else:
    KP = dict(conf.KeyPositions, **conf.CustomKeyPositions)
    split_keys = lambda kk: (k for k in (kk.split("-") if "combos" == table else [kk]) if k in KP)
    positions = [{"x": KP[k][0], "y": KP[k][1], "value": p["count"], "label": k}
                 for p in heatmap_stats for k in split_keys(p["key"])]
    events = [{"dt": str(e["dt"]), "data": [
                {"x": KP[k][0], "y": KP[k][1], "count": c, "key": k}
                for kk, c in e["keys"].items() for k in split_keys(kk)
              ]} for e in events]
end # if "mouse"
config = dict(conf.HeatmapDisplayOptions,
              **dict(conf.HeatmapDisplayOptions.get(input, {}), **conf.HeatmapDisplayOptions.get(table, {})))
for name in conf.InputFlags: config.pop(name, None)
end # for name
appidstr = "" if app_search else ",".join(map(str, app_ids or []))

%>
  var positions = {{! json.dumps(positions) }};
  var events = {{! json.dumps(events) }};
  var config = {{! json.dumps(config) }};
  window.addEventListener("load", function() {
    {{ "initMouseHeatmaps" if "mouse" == input else "initKeyboardHeatmap" }}(positions, events, config);
    initFullscreenControls();
%if conf.ProgramsEnabled:
    initAppsFilter("{{ make_url(appids=None, appnames=None) }}", "{{ app_search or "" }}", "{{ appidstr }}");
%end # if conf.ProgramsEnabled
    initToggles("a.toggle", "collapsed");
  });
</script>
