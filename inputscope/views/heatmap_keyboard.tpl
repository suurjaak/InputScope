%"""
Keyboard heatmap and statistics page.

Template arguments:
  input           "mouse"
  table           events table to show, like "keys" or "combos"
  period          period for events, if any (day like "2020-02-20" or month like "2020-02")
  days            list of available days
  count           count of all events
  counts          keyboard event counts
  counts_display  displayed event counts for keyboard combos
  events          list of replayable events
  stats           keyboard statistics
  tabledays       set of tables that have events for specified day

@author      Erki Suurjaak
@created     21.05.2015
@modified    27.01.2021
%"""
%WEBROOT = get_url("/")
%title = "%s %s" % (input.capitalize(), table)
%rebase("base.tpl", **locals())

<h3>{{ title }}</h3>{{ ", %s" % period if period else "" }} ({{ "{:,}".format(count) }})

<span id="replaysection">
  <input type="button" id="button_replay" value="Replay" />
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

<div id="tablelinks">
%for type, tbl in [(k, x) for k, tt in conf.InputTables for x in tt]:
    %if tbl == table:
  <span>{{ tbl }}</span>
    %else:
        %if period and tbl not in tabledays:
  <span class="inactive">{{ tbl }}</span>
        %elif period:
  <a href="{{ get_url("/%s/<table>/<period>" % type, table=tbl, period=period) }}">{{ tbl }}</a>
        %else:
  <a href="{{ get_url("/%s/<table>" % type, table=tbl) }}">{{ tbl }}</a>
        %end # if period
    %end # if tbl == table
%end # for type, tbl
</div>

%if events:
<div id="status">
<span id="statustext"><br /></span>
<span id="progressbar"></span>
<a href="javascript:;" title="Stop replay and reset heatmap" id="replay_stop">x</a>
</div>
%end # if events

<div id="heatmap" class="heatmap" style="width: {{ conf.KeyboardHeatmapSize[0] }}px; height: {{ conf.KeyboardHeatmapSize[1] }}px;"><img id="keyboard" src="{{ WEBROOT }}static/keyboard.svg" width="{{ conf.KeyboardHeatmapSize[0] }}" height="{{ conf.KeyboardHeatmapSize[1] }}" alt="" /></div>

<label for="show_heatmap" class="check_label"><input type="checkbox" id="show_heatmap" checked="checked" />Show heatmap</label>
<label for="show_keyboard" class="check_label"><input type="checkbox" id="show_keyboard" checked="checked" />Show keyboard</label>


<div id="tables">

  <table id="stats" class="{{ input }}">
%for key, val in stats:
    <tr><td>{{ key }}</td><td>{{ val }}</td></tr>
%end # for key, val
%if count > conf.MaxEventsForStats:
    <tr><td colspan="2">Statistics and heatmap limited to a maximum of {{ "{:,}".format(conf.MaxEventsForStats) }} events.</td></tr>
%end # if count > conf.MaxEventsForStats
  </table>

  <table>
    <tr><th>Key</th><th>Count</th></tr>
    %for item in counts_display:
    <tr><td>{{ item["key"] }}</td><td>{{ item["count"] }}</td></tr>
    %end # for item
  </table>

</div>

<script type="text/javascript">

  var RADIUS     = 20;
  var resumeFunc = null;
  var myHeatmap  = null;
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
                %data.append({"x": conf.KeyPositions[key][0], "y": conf.KeyPositions[key][1], "count": count, "key": key.encode("utf-8")})
            %end # for key
        %end # for fullkey
{dt: "{{ str(item["dt"]) }}", data: {{! data }}}, \\
    %end # for item
];
  var elm_heatmap = document.getElementById("heatmap");


  window.addEventListener("load", function() {

    var elm_step      = document.getElementById("replay_step"),
        elm_interval  = document.getElementById("replay_interval"),
        elm_button    = document.getElementById("button_replay"),
        elm_progress  = document.getElementById("progressbar"),
        elm_statusdiv = document.getElementById("status"),
        elm_status    = document.getElementById("statustext"),
        elm_show_hm   = document.getElementById("show_heatmap"),
        elm_show_kb   = document.getElementById("show_keyboard"),
        elm_stop      = document.getElementById("replay_stop"),
        elm_keyboard  = document.getElementById("keyboard");
    myHeatmap = h337.create({container: elm_heatmap, radius: RADIUS});
    if (positions.length) myHeatmap.setData({data: positions, max: positions[0].value});

    if (elm_show_kb) elm_show_kb.addEventListener("click", function() {
      elm_keyboard.style.display = this.checked ? "" : "none";
    });
    if (elm_show_hm) elm_show_hm.addEventListener("click", function() {
      elm_heatmap.getElementsByTagName("canvas")[0].style.display = this.checked ? "" : "none";
    });

    if (elm_button) elm_button.addEventListener("click", function() {
      if ("Replay" == elm_button.value) {
        elm_statusdiv.classList.add("playing");
        myHeatmap.setData({data: [], max: 0});
        elm_button.value = "Pause";
        replay(0);
      } else if ("Continue" != elm_button.value) {
        elm_button.value = "Continue";
      } else {
        elm_button.value = "Pause";
        resumeFunc && resumeFunc();
        resumeFunc = undefined;
      };
    });

    if (elm_stop) elm_stop.addEventListener("click", function() {
      elm_button.value = "Replay";
      elm_status.innerHTML = "<br />";
      elm_progress.style.width = 0;
      elm_statusdiv.classList.remove("playing");
      resumeFunc = undefined;
      myHeatmap.setData({data: positions, max: positions.length ? positions[0].value : 0});
    });

    var replay = function(index) {
      if (!elm_statusdiv.classList.contains("playing")) return;

      if (index <= events.length - 1) {
        var step = parseInt(elm_step.value);
        if (step > 1) {
          index = Math.min(index + step - 1, events.length - 1);
          myHeatmap.setData({data: events.slice(0, index + 1).reduce(function(o, v) { o.push.apply(o, v.data); return o; }, []), max: 0});
        } else myHeatmap.addData(events[index].data);

        var percent = (100 * index / events.length).toFixed() + "%";
        if (index == events.length - 1) percent = "100%";
        else if ("100%" == percent && index < events.length - 1) percent = "99%";
        elm_status.innerHTML = events[index]["dt"] + " " + percent;
        elm_progress.style.width = percent;

        var interval = elm_interval.max - elm_interval.value + parseInt(elm_interval.min);
        if ("Pause" != elm_button.value)
          resumeFunc = function() { setTimeout(replay, interval, index + 1); };
        else
          setTimeout(replay, interval, index + 1);

      } else {
        myHeatmap.setData({data: positions, max: positions.length ? positions[0].value : 0});
        elm_button.value = "Replay";
        elm_statusdiv.classList.remove("playing");
        replayevents = {};
      }
    };

  });
</script>
