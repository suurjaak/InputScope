%"""
Base template, with site layout and style.

Template arguments:
  title      page title, if any
  base       main content
  period     period for events, if any (day like "2020-02-20" or month like "2020-02")
  days       list of available days
  input      "mouse"|"keyboard"
  table      events table shown, moves|clicks|scrolls|keys|combos
  dbinfo     [(database info label, value)]

@author      Erki Suurjaak
@created     07.04.2015
@modified    26.01.2021
%"""
%WEBROOT = get_url("/")
%period, days = get("period", None), get("days", [])
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
    %prevperiod, nextperiod = None, None
    %if period and len(period) < 8:
    %    prevperiod = next((x["day"][:7] for x in days[::-1] if x["day"][:7] < period), None)
    %    nextperiod = next((x["day"][:7] for x in days       if x["day"][:7] > period), None)
    %else:
    %    dayidx = next((i for i, x in enumerate(days) if x["day"] == period), None)
    %    if dayidx is not None:
    %        prevperiod, nextperiod = (days[i]["day"] if 0 <= i < len(days) else None for i in [dayidx-1, dayidx+1])
    %    end # if dayidx is not None
    %    prevperiod = prevperiod or None if period else days[-1]["day"]
    %end # if period and len(period) < 8
    %if prevperiod:
  <a href="{{ get_url("/%s/<table>/<period>" % input, table=table, period=prevperiod) }}">&lt; {{ prevperiod }}</a>
    %end # if prevperiod

  <select id="dayselector">
    %if not period or not events:
    <option>- period -</option>
    %end # if not period
    %prevmonth = None
    %for d in days[::-1]:
        %if prevmonth != d["day"][:7]:
    <option{{! ' selected="selected"' if period == d["day"][:7] else "" }}>{{ d["day"][:7] }}</option>
        %end # if prevmonth != d["day"][:7]
    <option{{! ' selected="selected"' if period == d["day"] else "" }}>{{ d["day"] }}</option>
        %prevmonth = d["day"][:7]
    %end # for d
  </select>

    %if nextperiod:
  <a href="{{ get_url("/%s/<table>/<period>" % input, table=table, period=nextperiod) }}">{{ nextperiod }} &gt;</a>
    %end # if nextperiod
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
  Mouse and keyboard input visualizer. <a href="{{ conf.HomepageUrl }}" target="_blank">github</a>
</div>
</div>

<script type="text/javascript">
window.addEventListener("load", function() {
  document.location.hash = "";
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
