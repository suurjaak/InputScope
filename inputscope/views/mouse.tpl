%"""
Mouse statistics page.

Template arguments:
  table      mouse events table shown, moves|clicks|scrolls
  day        day for mouse events, if any
  events     list of mouse events
  positions  list of mouse positions with counts
  stats      mouse statistics

@author      Erki Suurjaak
@created     07.04.2015
@modified    06.05.2015
%"""
%WEBROOT = get_url("/")
%title = "Mouse %s" % table
%rebase("base.tpl", **locals())

<a href="{{get_url("/<input>", input="mouse")}}">Mouse index</a><br />
<h3>{{title}}</h3>{{", %s" % day if day else ""}} ({{len(events)}})

<input type="button" id="button_replay" value="Replay" />
<span class="range">
  <label for="replay_interval" class="range_label">speed</label>
  <input type="range" id="replay_interval" min="1" max="100" value="50" title="Animation interval" />
</span>
<span class="range">
  <label for="replay_step" class="range_label">step</label>
  <input type="range" id="replay_step" min="1" max="100" value="1" title="Points in each animation" />
</span>

<div id="status">
<span id="statustext"><br /></span>
<span id="progressbar"></span>
</div>

<div id="mouse_heatmap"></div>

<table>
%for key, val in get("stats", []):
  <tr><td>{{key}}</td><td>{{val}}</td></tr>
%end # for key, val
</table>

<script type="text/javascript">

  var RADIUS = {{3 if len(events) > 40000 else 5 if len(events) > 10000 else 10}};
  var resumeFunc = null;
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
  var elm_heatmap  = document.getElementById("mouse_heatmap");
  elm_heatmap.style.width = "{{conf.MouseHeatmapSize[0]}}px";
  elm_heatmap.style.height = "{{conf.MouseHeatmapSize[1]}}px";


  window.addEventListener("load", function() {

    var elm_step     = document.getElementById("replay_step"),
        elm_interval = document.getElementById("replay_interval"),
        elm_button   = document.getElementById("button_replay"),
        elm_progress = document.getElementById("progressbar"),
        elm_status   = document.getElementById("statustext");
    var myHeatmap = h337.create({container: elm_heatmap, radius: RADIUS});
    myHeatmap.setData({data: positions, max: positions.length ? positions[0].value : 0});


    var replay = function(index) {
      if (index <= events.length - 1) {

        var step = elm_step.value;
        for (var i = 0; i < step && index + i < events.length; i++)
          myHeatmap.addData(events[index + i]);
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
        elm_button.value = "Replay";
      }
    };


    elm_button.addEventListener("click", function() {
      if ("Replay" == elm_button.value) {
        myHeatmap.setData({data: [], max: positions.length ? positions[0].value : 0});
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

  });
</script>
