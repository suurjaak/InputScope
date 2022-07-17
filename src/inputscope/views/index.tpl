%"""
Index page.

Template arguments:
  stats      data statistics as {input: {count, first, last}}
  sessions   sessions statistics, as [{name, start, end, ..category counts}]

@author      Erki Suurjaak
@created     07.04.2015
@modified    16.07.2022
%"""
%import datetime
%from inputscope import conf
%from inputscope.util import format_stamp
%WEBROOT = get_url("/")
%page = "index"
%rebase("base.tpl", **locals())

<div>
<table class="totals">
%for input, data in stats.items():
  <tbody><tr><th>{{ input }}</th></tr><tr>
  <td>
    <div class="flex-row">
      <span>Total:</span>
%    if data["count"]:
      <a href="{{ get_url("/<input>", input=input) }}#{{ data["count"] }}">{{ "{:,}".format(data["count"]) }}</a>
      <span>from {{ data["first"] }} to {{ data["last"] }}</span>
%    else:
      0
%    end # if data["count"]
    </div>
  </td></tr></tbody>
%end # for input, data
</table>

%if sessions:
<table class="sessions">
  <tbody><tr><th>sessions</th></tr>
%end # if sessions
%for sess in sessions:
  <tr><td>
    <div class="flex-row">
      <span title="{{ sess["name"] }}">{{ sess["name"] }}:</span>
%    if sess["count"]:
      <a href="{{ get_url("/sessions/<session>", session=sess["id"]) }}#{{ sess["count"] }}">{{ "{:,}".format(sess["count"]) }}</a>
%    else:
      <span>0</span>
%    end # if sess["count"]
      <span>from {{ format_stamp(sess["start"]) }} {{ "to %s" % format_stamp(sess["end"]) if sess["end"] else "" }}</span>
    </div>
  </td></tr>
%end # for sess
%if sessions:
  </tbody>
</table>
%end # if sessions
</div>
