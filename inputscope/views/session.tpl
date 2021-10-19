%"""
Session page.

Template arguments:
  session   session data, as {name, start, end}
  data      session stats, as {category: {count, first, last}}

@author      Erki Suurjaak
@created     15.10.2021
@modified    17.10.2021
%"""
%import datetime
%from inputscope import conf
%WEBROOT = get_url("/")
%rebase("base.tpl", **locals())

<div>
<table>

<table>
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
