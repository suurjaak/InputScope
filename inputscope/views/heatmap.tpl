%"""
Mouse or keyboard heatmap and statistics page.

Template arguments:
  table      events table to show, like "clicks" or "keys"
  day        day for events, if any
  days       list of available days
  input      "mouse"|"keyboard"
  events     list of all events
  counts     keyboard event counts
  positions  mouse position counts
  stats      keyboard statistics

@author      Erki Suurjaak
@created     21.05.2015
@modified    21.05.2015
%"""
%WEBROOT = get_url("/")
%title = "%s %s" % (input.capitalize(), table)
%rebase("base.tpl", **locals())

<h3>{{title}}</h3>{{", %s" % day if day else ""}} ({{len(events)}})

<span id="replaysection">
  <input type="button" id="button_replay" value="Replay" />
  <span class="range">
    <label for="replay_interval" class="range_label">speed</label>
    <input type="range" id="replay_interval" min="1" max="100" value="50" title="Animation interval" />
  </span>
  <span class="range">
    <label for="replay_step" class="range_label">step</label>
    <input type="range" id="replay_step" min="1" max="100" value="1" title="Points in each animation" />
  </span>
</span>

%if day:
<div id="tablelinks">
%for type, tbl in [(k, x) for k, tt in conf.InputTables for x in tt]:
    %if tbl == table:
  <span>{{tbl}}</span>
    %else:
  <a href="{{get_url("/%s/<table>/<day>" % type, table=tbl, day=day)}}">{{tbl}}</a>
    %end # if tbl == table
%end # for type, tbl
</div>
%end # if day

<div id="status">
<span id="statustext"><br /></span>
<span id="progressbar"></span>
</div>

%if "keyboard" == input:
<div id="heatmap"><img id="keyboard" src="{{WEBROOT}}static/keyboard.svg" width="{{conf.KeyboardHeatmapSize[0]}}" height="{{conf.KeyboardHeatmapSize[1]}}" alt=""/></div>

<label for="show_heatmap" class="check_label"><input type="checkbox" id="show_heatmap" checked="checked" />Show heatmap</label>
<label for="show_keyboard" class="check_label"><input type="checkbox" id="show_keyboard" checked="checked" />Show keyboard</label>
%else:
<div id="heatmap" class="mouse"></div>
%end # if "keyboard"



<div id="tables">

  <table id="stats" class="{{input}}">
%for key, val in stats:
    <tr><td>{{key}}</td><td>{{val}}</td></tr>
%end # for key, val
  </table>

%if "keyboard" == input:
  <table>
    <tr><th>Key</th><th>Count</th></tr>
    %for item in counts_display:
    <tr><td>{{item["key"]}}</td><td>{{item["count"]}}</td></tr>
    %end # for item
  </table>
%end # if "keyboard"

</div>

<script type="text/javascript">

  var RADIUS = {{20 if "keyboard" == input else 3 if len(events) > 40000 else 5 if len(events) > 10000 else 10}};
  var resumeFunc = null;
%if "keyboard" == input:
  var positions = [\\
    %for item in counts:
        %data = []
        %keys = item["key"].split("-") if "combos" == table else [item["key"]]
        %for key in keys:
            %if key not in conf.KeyPositions:
                %continue # for key
            %end # if key not in
{x: {{conf.KeyPositions[key][0]}}, "y": {{conf.KeyPositions[key][1]}}, value: {{item["count"]}}, label: "{{key}}"}, \\
        %end # for key
    %end # for item
];
  var events = [\\
    %for item in collatedevents:
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
{dt: "{{item["dt"].isoformat()}}", data: {{!data}}}, \\
    %end # for item
];
%else:
  var positions = [\\
    %for pos in positions:
{x: {{pos["x"]}}, y: {{pos["y"]}}, value: {{pos.get("count", 1)}}}, \\
    %end # for pos
];
  var events = [\\
    %for pos in events:
{x: {{pos["x"]}}, y: {{pos["y"]}}, dt: "{{pos["dt"].isoformat()}}"}, \\
    %end # for pos
];
%end # if "keyboard"

  var elm_heatmap  = document.getElementById("heatmap");
  %mapsize = conf.KeyboardHeatmapSize if "keyboard" == input else conf.MouseHeatmapSize
  elm_heatmap.style.width = "{{mapsize[0]}}px";
  elm_heatmap.style.height = "{{mapsize[1]}}px";

  window.addEventListener("load", function() {

    var elm_step     = document.getElementById("replay_step"),
        elm_interval = document.getElementById("replay_interval"),
        elm_button   = document.getElementById("button_replay"),
        elm_progress = document.getElementById("progressbar"),
        elm_status   = document.getElementById("statustext"),
        elm_show_hm  = document.getElementById("show_heatmap"),
        elm_show_kb  = document.getElementById("show_keyboard"),
        elm_keyboard = document.getElementById("keyboard");
    var myHeatmap = h337.create({container: elm_heatmap, radius: RADIUS});
    if (positions.length) myHeatmap.setData({data: positions, max: positions[0].value});

    if (elm_show_kb) elm_show_kb.addEventListener("click", function() {
      elm_keyboard.style.display = this.checked ? "" : "none";
    });
    if (elm_show_hm) elm_show_hm.addEventListener("click", function() {
      elm_heatmap.getElementsByTagName("canvas")[0].style.display = this.checked ? "" : "none";
    });

    elm_button.addEventListener("click", function() {
      if ("Replay" == elm_button.value) {
        myHeatmap.setData({data: [], max: 0});
        myHeatmap.setData({data: [], max: {{!0 if "keyboard" == input else "positions.length ? positions[0].value : 0"}}});
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

    var replay = function(index) {
      if (index <= events.length - 1) {

        var step = elm_step.value;
        for (var i = 0; i < step && index + i < events.length; i++)
          myHeatmap.addData(events[index + i].data || events[index + i]);
        index += i - 1;

        var percent = (100 * index / events.length).toFixed() + "%";
        percent = (index == events.length - 1) ? "100%" : percent;
        elm_status.innerHTML = events[index]["dt"] + " " + percent;
        elm_progress.style.width = percent;

        var interval = elm_interval.max - elm_interval.value;
        if ("Pause" != elm_button.value)
          resumeFunc = function() { setTimeout(replay, interval, index + 1); };
        else
          setTimeout(replay, interval, index + 1);

      } else {
%if "keyboard" == input:
        myHeatmap.setData({data: positions, max: positions.length ? positions[0].value : 0});
%end # if "keyboard"
        elm_button.value = "Replay";
      }
    };

  });
</script>
