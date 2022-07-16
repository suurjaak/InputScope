%"""
Session page.

Template arguments:
  session   session data, as {name, start, end}
  data      session stats, as {category: {count, first, last}}

@author      Erki Suurjaak
@created     15.10.2021
@modified    16.07.2022
%"""
%from inputscope import conf
%WEBROOT = get_url("/")
%page = "session index"
%rebase("base.tpl", **locals())

<div>

<table id="stats" class="sessions">
  <tr>
    <td>Session name</td>
    <td title="{{ session["name"] }}">{{ session["name"] }}</td>
  </tr>
%for key, val in sessioninfo:
    <tr><td>{{ key }}</td><td>{{ val }}</td></tr>
%end # for key
</tr></table>

<table class="totals">
%for input, table in ((k, t) for k, tt in conf.InputTables for t in tt):
%    data = stats.get(table, {})
%    if not data.get("count"):
%        continue # for table
%    end
  <tbody>
  <tr><th>{{ table }}</th></tr>
  <tr><td>Total:</td><td><a href="{{ get_url("/sessions/<session>/<input>/<table>", session=session["id"], input=input, table=table) }}#{{ data["count"] }}">{{ "{:,}".format(data["count"]) }}</a></td></tr>
  <tr><td>Days:</td>
    <td id="{{ table }}_periods" class="periods">
    <div class="periods">
%   for item in data["periods"]:
      <a class="{{ item["class"] }}" href="{{ get_url("/sessions/<session>/<input>/<table>/<period>", session=session["id"], input=input, table=table, period=item["period"]) }}#{{ item["count"] }}">{{ item["period"] }}</a>
      <span>({{ "{:,}".format(item["count"])  }})</span><br />
%    end # for item
    </div>
    </td>
  </tr>
  </tbody>
%end # for table, data
</table>
</div>
