%"""
Base template, with site layout and style.

Template arguments:
  title      page title, if any
  base       main content
  period     period for events, if any (day like "2020-02-20" or month like "2020-02")
  days       list of available days
  input      "mouse"|"keyboard"
  page       page being shown like "index" or "input"
  table      events table shown, moves|clicks|scrolls|keys|combos
  session    session data, if any
  dbinfo     [(database info label, value)]

------------------------------------------------------------------------------
This file is part of InputScope - mouse and keyboard input visualizer.
Released under the MIT License.

@author      Erki Suurjaak
@created     07.04.2015
@modified    15.04.2024
------------------------------------------------------------------------------
%"""
%import os, bottle
%from inputscope.util import format_session
%WEBROOT = get_url("/")
%period, days, session = get("period", None), get("days", []), get("session", None)
%bodycls = " ".join(set(filter(bool, get("page", "").split() + ["session" if session else ""])))
<!DOCTYPE html>
<html>
<head>
  <title>{{ conf.Title }}{{ " - " + title if get("title") else "" }}</title>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name="Author" content="Erki Suurjaak">
  <link rel="icon" type="image/x-icon" href="{{ WEBROOT }}static/icon.ico" />
  <link rel="stylesheet" href="{{ WEBROOT }}static/site.css" />
  <script src="{{ WEBROOT }}static/heatmap.min.js"></script>
  <script src="{{ WEBROOT }}static/site.js"></script>
</head>
<body{{! ' class="%s"' % bodycls if bodycls else "" }}>
<div id="header" class="flex-row">

  <span id="headerlinks">
    <a href="{{ WEBROOT }}" id="indexlink">{{ conf.Title }}</a>
    <span id="inputlinks">
%for type in ["mouse", "keyboard"]:
    <a href="{{ get_url("/<input>", input=type) }}">{{ type }}</a>
%end # for x
    </span>
  </span>

%if session or days:
<span class="flex-row">
%end # if session or days

%if session:
  <span id="session" title="session {{ format_session(session, maxlen=0, quote=True) }}">
%if get("input"):
    <a href="{{ get_url("/sessions/<session>", session=session["id"]) }}">
%end # if
    SESSION
    <div>
      {{ session["name"] }}
    </div>
%if get("input"):
    </a>
%end # if
  </span>
%end # if defined("session")

%if days:
<span id="daysection" class="flex-row">
    %prevperiod, nextperiod = None, None
    %if period and len(period) < 5:
    %    prevperiod = next((x["day"][:4] for x in days[::-1] if x["day"][:4] < period), None)
    %    nextperiod = next((x["day"][:4] for x in days       if x["day"][:4] > period), None)
    %elif period and len(period) < 8:
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
  <a href="{{ make_url(period=prevperiod) }}">&lt; {{ prevperiod }}</a>
    %else:
  <a></a>
    %end # if prevperiod

  <select id="dayselector">
    %if not period or not events:
    <option>- period -</option>
    %end # if not period
    %prevmonth, prevyear = None, None
    %for d in days[::-1]:
        %if prevyear != d["day"][:4] and not session:
    <option{{! ' selected="selected"' if period == d["day"][:4] else "" }}>{{ d["day"][:4] }}</option>
        %end # if prevyear != d["day"][:4]
        %if prevmonth != d["day"][:7] and not session:
    <option{{! ' selected="selected"' if len(period or "") == 7 and period == d["day"][:7] else "" }}>{{ d["day"][:7] }}</option>
        %end # if prevmonth != d["day"][:7]
    <option{{! ' selected="selected"' if period == d["day"] else "" }}>{{ d["day"] }}</option>
        %prevmonth, prevyear = d["day"][:7], d["day"][:4]
    %end # for d
  </select>

    %if nextperiod:
  <a href="{{ make_url(period=nextperiod) }}">{{ nextperiod }} &gt;</a>
    %else:
  <a></a>
    %end # if nextperiod
</span>
%end # if days

%if session or days:
</span>
%end # if session or days

</div>

<div id="content">
{{! base }}
</div>

<div id="overlay" class="hidden">
  <div id="overshadow"></div>
  <div id="overcontent">
    <table class="outlined">
%for k, v in dbinfo:
      <tr><td>{{ k }}:</td><td>{{ v }}</td></tr>
%end # for k, v
    </table>
%if conf.LicensePath:
    <div>Licensing for bundled software:
      <a href="{{ WEBROOT }}static/{{ bottle.urlquote(os.path.basename(conf.LicensePath)) }}" target="_blank">
        {{ os.path.basename(conf.LicensePath) }}
      </a>
    </div>
%end # if conf.LicensePath
    <input type="button" id="overlayclose" value="OK" />
  </div>
</div>

<div id="footer" class="flex-row">
  <a href="#" id="overlaylink">information</a>
  <span>Mouse and keyboard input visualizer.</span>
  <a href="{{ conf.HomepageUrl }}" target="_blank">github</a>
</div>

<script type="text/javascript">
window.addEventListener("load", function() {
  document.location.hash = "";
  var elm_overlay = document.getElementById("overlay");
  var toggleOverlay = function(evt) {
    elm_overlay.classList.toggle("hidden");
    evt && evt.preventDefault();
  };

  document.getElementById("overlaylink") .addEventListener("click", toggleOverlay);
  document.getElementById("overlayclose").addEventListener("click", toggleOverlay);
  document.getElementById("overshadow")  .addEventListener("click", toggleOverlay);
  document.body.addEventListener("keydown", function(evt) {
    if (evt.keyCode == 27 && !elm_overlay.classList.contains("hidden")) toggleOverlay();
  });

%if days:
  document.getElementById("dayselector").addEventListener("change", function() {
    window.location.href = "{{ make_url(period="\\t\\n\\t") }}/".replace("\t\n\t", this.value);
  });
%end # if days
});
</script>
</body>
</html>
