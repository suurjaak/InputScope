%"""
Session page.

Template arguments:
  session   session data, as {name, start, end}
  data      session stats, as {category: {count, first, last}}

------------------------------------------------------------------------------
This file is part of InputScope - mouse and keyboard input visualizer.
Released under the MIT License.

@author      Erki Suurjaak
@created     15.10.2021
@modified    16.04.2024
------------------------------------------------------------------------------
%"""
%from inputscope import conf
%from inputscope.util import format_weekday
%WEBROOT = get_url("/")
%page = "session index"
%rebase("base.tpl", **locals())

<div>

<table id="stats" class="sessions outlined">
  <tr>
    <td>Session name</td>
    <td title="{{ session["name"] }}">{{ session["name"] }}</td>
  </tr>
%for key, val in sessioninfo:
    <tr><td>{{ key }}</td><td>{{ val }}</td></tr>
%end # for key
</tr></table>

%for input, table in ((k, t) for k, tt in conf.InputTables for t in tt):
%    data = stats.get(table, {})
%    if not data.get("count"):
%        continue # for table
%    end
<div class="data">
  <a href="javascript:;" class="toggle" data-input="{{ table }}" title="Toggle days">&ndash;</a>
  <table class="totals">
  <tr><th>{{ table }}</th></tr>
  <tr><td>Total:</td><td><a href="{{ get_url("/sessions/<session>/<input>/<table>", session=session["id"], input=input, table=table) }}#{{ data["count"] }}">{{ "{:,}".format(data["count"]) }}</a></td></tr>
  <tr><td>Days:</td>
    <td id="{{ table }}_periods" class="periods">
    <div class="count">{{ len([v for v in data["periods"] if "day" == v["class"]]) }}</div>
    <div class="periods">
%   for item in data["periods"]:
      <div class="flex-row">
        <a class="{{ item["class"] }}" href="{{ get_url("/sessions/<session>/<input>/<table>/<period>", session=session["id"], input=input, table=table, period=item["period"]) }}#{{ item["count"] }}">
        {{ item["period"] }}
%        if "day" == item["class"]:
%            try:
          <span class="weekday" title="{{ format_weekday(item["period"], long=True) }}">{{ format_weekday(item["period"]) }}</span>
%            except Exception: pass
%            end # try
%        end # if "day"
        </a>
        <span>({{ "{:,}".format(item["count"])  }})</span><br />
      </div>
%    end # for item
    </div>
    </td>
  </tr>
  </table>
</div>
%end # for table, data
</div>

<script type="text/javascript">
  window.addEventListener("load", function() { initToggles("a.toggle", "collapsed"); });
</script>
