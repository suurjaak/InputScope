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

@author      Erki Suurjaak
@created     07.04.2015
@modified    16.07.2022
%"""
%from inputscope.util import format_session
%WEBROOT = get_url("/")
%INPUTURL, URLARGS = ("/<input>", dict(input=input)) if get("input") else ("/", {})
%period, days, session = get("period", None), get("days", []), get("session", None)
%if session:
%    INPUTURL, URLARGS = "/sessions/<session>" + INPUTURL, dict(URLARGS, session=session["id"])
%end # if session
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
  <a href="{{ get_url("%s/<table>/<period>" % INPUTURL, table=table, period=prevperiod, **URLARGS) }}">&lt; {{ prevperiod }}</a>
    %else:
  <a></a>
    %end # if prevperiod

  <select id="dayselector">
    %if not period or not events:
    <option>- period -</option>
    %end # if not period
    %prevmonth = None
    %for d in days[::-1]:
        %if prevmonth != d["day"][:7] and not session:
    <option{{! ' selected="selected"' if period == d["day"][:7] else "" }}>{{ d["day"][:7] }}</option>
        %end # if prevmonth != d["day"][:7]
    <option{{! ' selected="selected"' if period == d["day"] else "" }}>{{ d["day"] }}</option>
        %prevmonth = d["day"][:7]
    %end # for d
  </select>

    %if nextperiod:
  <a href="{{ get_url("%s/<table>/<period>" % INPUTURL, table=table, period=nextperiod, **URLARGS) }}">{{ nextperiod }} &gt;</a>
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

<div id="overlay">
  <div id="overshadow"></div>
  <div id="overcontent">
    <table>
%for k, v in dbinfo:
      <tr><td>{{ k }}:</td><td>{{ v }}</td></tr>
%end # for k, v
    </table>
    <input type="button" id="overlayclose" value="OK" />
  </div>
</div>

<div id="footer" class="flex-row">
  <a href="#" id="overlaylink">database info</a>
  <span>Mouse and keyboard input visualizer.</span>
  <a href="{{ conf.HomepageUrl }}" target="_blank">github</a>
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
    window.location.href = "{{ get_url("%s/<table>" % INPUTURL, table=table, **URLARGS) }}/" + this.value;
  });
%end # if days
});
</script>
</body>
</html>
