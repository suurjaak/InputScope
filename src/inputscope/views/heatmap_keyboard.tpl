%"""
Keyboard heatmap and statistics page.

Template arguments:
  input           "keyboard"
  table           events table to show, like "keys" or "combos"
  period          period for events, if any (day like "2020-02-20" or month like "2020-02")
  days            list of available days
  count           count of all events
  counts          keyboard event counts, as {key: count}
  counts_display  displayed event counts for keyboard combos, as {key: count}
  events          list of replayable events
  session         session data, if any
  stats           keyboard statistics
  apps            list of all registered applications, as [{id, path}]
  app_ids         list of application IDs currently filtered by
  app_search      application filter search text
  app_stats       per-application keyboard statistics, as OrderedDict({id: {path, total, ?top}})
  tabledays       set of tables that have events for specified day

@author      Erki Suurjaak
@created     21.05.2015
@modified    29.07.2023
%"""
%import json, os, re
%import bottle
%from inputscope.util import format_weekday
%WEBROOT = get_url("/")
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

<div class="heatmap-container" style="margin: 0 calc(-10rem + {{ (700 - conf.KeyboardHeatmapSize[0]) // 2 }}px - 2px);">
  <div class="heatmap {{ input }}" style="width: {{ conf.KeyboardHeatmapSize[0] }}px; height: {{ conf.KeyboardHeatmapSize[1] }}px;"><img id="keyboard" src="{{ WEBROOT }}static/keyboard.svg" width="{{ conf.KeyboardHeatmapSize[0] }}" height="{{ conf.KeyboardHeatmapSize[1] }}" alt="" /></div>
  <div class="heatmap_helpers">
%if apps:
    <a id="apps_form_show" title="Select applications">applications</a>
%end # if apps
    <label for="show_heatmap" class="check_label"><input type="checkbox" id="show_heatmap" checked="checked" />Show heatmap</label>
    <label for="show_keyboard" class="check_label"><input type="checkbox" id="show_keyboard" checked="checked" />Show keyboard</label>
  </div>

%if apps:
  <form id="apps_form" class="hidden">
  <input type="search" value="{{ app_search or "" }}" 
         placeholder="Filter applications" title="Enter words or phrases to filter applications by" />
    <div class="items"><table>
    %for item in apps:
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

  <table id="stats" class="{{ input }} outlined">
%for key, val in stats:
    <tr><td>{{ key }}</td><td>{{ val }}</td></tr>
%end # for key, val
%if count > conf.MaxEventsForStats:
    <tr><td colspan="2">Statistics and heatmap limited to a maximum of {{ "{:,}".format(conf.MaxEventsForStats) }} events.</td></tr>
%end # if count > conf.MaxEventsForStats
  </table>

  <table id="counts" class="outlined">
    <tr><th>Key</th><th>Count</th></tr>
    %for item in counts_display:
    <tr><td>{{ item["key"] }}</td><td>{{ item["count"] }}</td></tr>
    %end # for item
  </table>

%if len([x for x in app_stats.values() if x["total"]]) > 1:
  <table id="app_stats" class="outlined">
    <tr><th>Application</th><th>Most used</th><th>Total</th></tr>
    %for item in (x for x in app_stats.values() if x.get("top")):
    <tr>
      <td title="{{ item["path"] }}">{{ os.path.split(item["path"] or "")[-1] or "(unknown)" }}</td>
      <td>{{ ", ".join(item["top"]) }}</td>
      <td>{{ "{:,}".format(item["total"]) }}</td>
    </tr>
    %end # for item
  </table>
%end # if app_stats and ..

</div>

<script type="text/javascript">
  var positions  = [\\
    %for item in counts:
        %data = []
        %keys = item["key"].split("-") if "combos" == table else [item["key"]]
        %for key in keys:
            %if key not in conf.KeyPositions:
                %continue # for key
            %end # if key not in
{x: {{ conf.KeyPositions[key][0] }}, "y": {{ conf.KeyPositions[key][1] }}, value: {{ item["count"] }}, label: "{{ key }}"}, \\
        %end # for key
    %end # for item
];
  var events     = [\\
    %for item in events:
        %data = []
        %for fullkey, count in item["keys"].items():
            %keys = fullkey.split("-") if "combos" == table else [fullkey]
            %for key in keys:
                %if key not in conf.KeyPositions:
                    %continue # for key
                %end # if key not in
                %data.append({"x": conf.KeyPositions[key][0], "y": conf.KeyPositions[key][1],
                %             "count": count, "key": json.dumps(key)})
            %end # for key
        %end # for fullkey
{dt: "{{ str(item["dt"]) }}", data: {{! data }}}, \\
    %end # for item
];

  window.addEventListener("load", function() {
%appidstr = "" if app_search else ",".join(map(str, app_ids or []))
    initKeyboardHeatmap(positions, events);
    initAppsFilter("{{ make_url(appids=None, appnames=None) }}", "{{ app_search or "" }}", "{{ appidstr }}");
  });
</script>
