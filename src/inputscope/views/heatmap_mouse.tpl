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
  tabledays       set of tables that have events for specified day

@author      Erki Suurjaak
@created     21.05.2015
@modified    16.07.2022
%"""
%WEBROOT = get_url("/")
%INPUTURL, URLARGS = ("/sessions/<session>", dict(session=session["id"])) if get("session") else ("", {})
%title = "%s %s" % (input.capitalize(), table)
%rebase("base.tpl", **locals())

<div id="tablelinks">
%for type, tbl in [(k, x) for k, tt in conf.InputTables for x in tt]:
    %if tbl == table:
  <span>{{ tbl }}</span>
    %elif tabledays and tbl not in tabledays:
  <span class="inactive">{{ tbl }}</span>
    %elif period:
  <a href="{{ get_url("%s/<input>/<table>/<period>" % INPUTURL, input=type, table=tbl, period=period, **URLARGS) }}">{{ tbl }}</a>
    %else:
  <a href="{{ get_url("%s/<input>/<table>" % INPUTURL, input=type, table=tbl, **URLARGS) }}">{{ tbl }}</a>
    %end # if tbl == table
%end # for type, tbl
</div>

<div id="heading" class="flex-row">
  <span>
    <h3>{{ title }}</h3>{{ ", %s" % period if period else "" }} ({{ "{:,}".format(count) }})
  </span>

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
</div>

%if events:
<div id="status">
<span id="statustext"><br /></span>
<span id="progressbar"></span>
<a href="javascript:;" title="Stop replay and reset heatmap" id="replay_stop">x</a>
</div>
%end # if events

    %for display in positions:
<div id="heatmap{{ display }}" class="heatmap {{ input }}" style="width: {{ conf.MouseHeatmapSize[0] }}px; height: {{ conf.MouseHeatmapSize[1] }}px; margin-left: calc(-10rem + {{ (700 - conf.MouseHeatmapSize[0]) // 2 }}px - 1px);"></div>
    %end # for display



<div id="tables">

  <table id="stats" class="{{ input }}">
%for key, val in stats:
    <tr><td>{{ key }}</td><td>{{ val }}</td></tr>
%end # for key, val
%if count > conf.MaxEventsForStats:
    <tr><td colspan="2">Statistics and heatmap limited to a maximum of {{ "{:,}".format(conf.MaxEventsForStats) }} events.</td></tr>
%end # if count > conf.MaxEventsForStats
  </table>

</div>

<script type="text/javascript">

  var RADIUS     = 10;
  var resumeFunc = null;
  var myHeatmaps = {};
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

    var elm_step      = document.getElementById("replay_step"),
        elm_interval  = document.getElementById("replay_interval"),
        elm_button    = document.getElementById("button_replay"),
        elm_progress  = document.getElementById("progressbar"),
        elm_statusdiv = document.getElementById("status"),
        elm_status    = document.getElementById("statustext"),
        elm_stop      = document.getElementById("replay_stop");
    var replayevents = {};
    %for display in positions:
    myHeatmaps[{{ display }}] = h337.create({container: document.getElementById("heatmap{{ display }}"), radius: RADIUS});
    %end # for display
    %for display in positions:
    myHeatmaps[{{ display }}].setData({data: positions[{{ display }}], max: positions[{{ display }}].length ? positions[{{ display }}][0].value : 0});
    %end # for display

    if (elm_button) elm_button.addEventListener("click", function() {
      if ("Replay" == elm_button.value) {
        elm_statusdiv.classList.add("playing");
        replayevents = {};
        Object.keys(myHeatmaps).forEach(function(display) {
          myHeatmaps[display].setData({data: [], max: positions[display].length ? positions[display][0].value : 0});
        });
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
      replayevents = {};
      Object.keys(myHeatmaps).forEach(function(display) {
        myHeatmaps[display].setData({data: positions[display], max: positions[display].length ? positions[display][0].value : 0});
      });
    });

    var replay = function(index) {
      if (!elm_statusdiv.classList.contains("playing")) return;

      if (index <= events.length - 1) {
        var step = parseInt(elm_step.value);
        if (step > 1) {
          var index2 = Math.min(index + step - 1, events.length - 1);
          var changeds = {}; // {display index: true}
          for (var i = index; i <= index2; i++) {
            var evt = events[i];
            changeds[evt.display] = true;
            (replayevents[evt.display] = replayevents[evt.display] || []).push(evt);
          };
          index = index2;
          Object.keys(changeds).forEach(function(display) {
            myHeatmaps[display].setData({data: replayevents[display], max: 0});
          });
        } else {
          myHeatmaps[events[index].display].addData(events[index]);
          (replayevents[events[index].display] = replayevents[events[index].display] || []).push(events[index]);
        };

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
        elm_button.value = "Replay";
        elm_statusdiv.classList.remove("playing");
        replayevents = {};
      }
    };

  });
</script>
