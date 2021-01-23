%"""
Base template, with site layout and style.

Template arguments:
  title      page title, if any
  base       main content
  days       list of available days
  input      "mouse"|"keyboard"
  table      events table shown, moves|clicks|scrolls|keys|combos
  dbinfo     [(database info label, value)]

@author      Erki Suurjaak
@created     07.04.2015
@modified    21.05.2015
%"""
%WEBROOT = get_url("/")
%days = get("days", [])
<!DOCTYPE html>
<html>
<head>
  <title>{{ conf.Title }}{{ " - " + title if get("title") else "" }}</title>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name="Author" content="Erki Suurjaak">
  <link rel="icon" type="image/x-icon" href="{{ WEBROOT }}static/icon.ico" />
  <link rel="stylesheet" href="{{ WEBROOT }}static/site.css" />
  <script src="{{ WEBROOT }}static/heatmap.min.js"></script>
</head>
<body>
<div id="header" style="position: relative;">

  <span id="headerlinks">
    <a href="{{ WEBROOT }}" id="indexlink">{{ conf.Title }}</a>
    <span id="inputlinks">
%for x in ["mouse", "keyboard"]:
    <a href="{{ get_url("/<input>", input=x) }}">{{ x }}</a>
%end # for x
    </span>
  </span>

%if days:
<span id="daysection">
    %dayidx = next((i for i, x in enumerate(days) if x["day"] == day), None)
    %prevday, nextday = (days[x]["day"] if 0 <= x < len(days) else None for x in [dayidx-1, dayidx+1]) if dayidx is not None else [None]*2
    %prevday = prevday if day and events else days[-1]["day"]
  <a href="{{ get_url("/%s/<table>/<day>" % input, table=table, day=prevday) }}">{{ "< %s" % prevday if prevday else "" }}</a>

  <select id="dayselector">
    %if not day or not events:
    <option>- day -</option>
    %end # if not day
    %for d in days[::-1]:
    <option{{! ' selected="selected"' if day == d["day"] else "" }}>{{ d["day"] }}</option>
    %end # for d
  </select>

  <a href="{{ get_url("/%s/<table>/<day>" % input, table=table, day=nextday) }}">{{ "%s >" % nextday if nextday else "" }}</a>
</span>
%end # if days

</div>

<div id="content" style="position: relative;">
{{! base }}
</div>

<div id="overlay">
  <div id="overshadow"></div>
  <div id="overcontent">
    <table>
%for k, v in dbinfo:
      <tr><td>{{ k }}:</td><td>{{ v }}</td></tr>
%end # for k, v
    </table>
    <button id="overlayclose">OK</button>
  </div>
</div>

<div id="footer">
<div>
  <a href="#" id="overlaylink">database info</a>
  Mouse and keyboard input visualizer. &copy; 2015 Erki Suurjaak. <a href="{{ conf.HomepageUrl }}" target="_blank">github</a>
</div>
</div>

<script type="text/javascript">
window.addEventListener("load", function() {
  var elm_overlay = document.getElementById("overlay");
  var toggleOverlay = function(evt) {
    elm_overlay.classList.toggle("visible");
    evt && evt.preventDefault();
  };

  document.getElementById("overlaylink").addEventListener("click", toggleOverlay);
  document.getElementById("overlayclose").addEventListener("click", toggleOverlay);
  document.getElementById("overshadow").addEventListener("click", toggleOverlay);
  document.body.addEventListener("keydown", function(evt) {
    if (evt.keyCode == 27 && elm_overlay.classList.contains("visible")) toggleOverlay();
  });

%if days:
  document.getElementById("dayselector").addEventListener("change", function() {
    window.location.href = "{{ get_url("/%s/<table>" % input, table=table) }}/" + this.value;
  });
%end # if days
});
</script>
</body>
</html>
