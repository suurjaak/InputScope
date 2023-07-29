%"""
Mouse heatmap and statistics page.

Template arguments:
  input           "mouse"
  table           events table to show, like "clicks" or "keys"
  period          period for events, if any (day like "2020-02-20" or month like "2020-02")
  days            list of available days
  count           count of all events
  events          list of replayable events, as [{x, y, display, dt}]
  positions       mouse position counts, as {display: [{x, y, count}, ]}
  session         session data, if any
  stats           mouse statistics, as [(label, text)]
  apps            list of all registered applications, as [{id, path}]
  app_ids         list of application IDs currently filtered by
  app_search      application filter search text
  app_stats       per-application keyboard statistics, as OrderedDict({id: {path, total, ?cols: {label: count}}})
  tabledays       set of tables that have events for specified day

@author      Erki Suurjaak
@created     21.05.2015
@modified    29.07.2023
%"""
%import os, re
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

<div class="heatmap-container" style="margin: 0 calc(-10rem + {{ (700 - conf.MouseHeatmapSize[0]) // 2 }}px - 2px);">
%for i, display in enumerate(positions or [None]):
  <div class="heatmap {{ input }}" style="width: {{ conf.MouseHeatmapSize[0] }}px; height: {{ conf.MouseHeatmapSize[1] }}px;"></div>
  <div class="heatmap_helpers">
    %if apps:
    <a id="apps_form_show" title="Select applications">applications</a>
    %end # if apps
    <a class="fullscreen" title="Expand heatmap to full screen">full screen</a>
  </div>

    %if apps and not i:
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
    %end # if apps and not i
%end # for i, display
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

%if len([x for x in app_stats.values() if x["total"]]) > 1:
%    labels = []
%    for label in (l for x in app_stats.values() for l in x.get("cols", [])):
%        labels.append(label) if label not in labels else label
%    end # for label
  <table id="app_stats" class="{{ input }} outlined">
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
      <td>{{ "{:,}".format(v) if isinstance(v, int) else v }}</td>
%        end # for label
      <td>{{ "{:,}".format(item["total"]) }}</td>
    </tr>
%    end # for item
  </table>
%end # if app_stats and ..

</div>

<script type="text/javascript">

  var positions  = {\\
    %for display, poses in positions.items():
{{ display }}: [\\
        %for pos in poses:
{x: {{ pos["x"] }}, y: {{ pos["y"] }}, value: {{ pos.get("count", 1) }}}, \\
        %end # for pos
], \\
    %end # for display, poses
};
  var events     = [\\
    %for evt in events:
{x: {{ evt["x"] }}, y: {{ evt["y"] }}, display: {{ evt["display"] }}, dt: "{{ str(evt["dt"]) }}"}, \\
    %end # for evt
];

  window.addEventListener("load", function() {
%appidstr = "" if app_search else ",".join(map(str, app_ids or []))
    initMouseHeatmaps(positions, events);
    initAppsFilter("{{ make_url(appids=None, appnames=None) }}", "{{ app_search or "" }}", "{{ appidstr }}");
  });
</script>
