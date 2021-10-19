%"""
Index page.

Template arguments:
  stats      data statistics as {input: {count, first, last}}
  sessions   sessions statistics, as [{name, start, end, ..category counts}]

@author      Erki Suurjaak
@created     07.04.2015
@modified    18.10.2021
%"""
%import datetime
%from inputscope import conf
%from inputscope.util import format_stamp
%WEBROOT = get_url("/")
%page = "index"
%rebase("base.tpl", **locals())

<div>
<table>
%for input, data in stats.items():
  <tbody><tr><th>{{ input }}</th><th></th><th></th></tr><tr>
  <td>Total:</td>
%    if data["count"]:
      <td><a href="{{ get_url("/<input>", input=input) }}#{{ data["count"] }}">{{ "{:,}".format(data["count"]) }}</a></td>
      <td>from {{ data["first"] }} to {{ data["last"] }}</td>
%    else:
      <td>0</td>
%    end # if data["count"]
  </tr></tbody>
%end # for input, data
</table>

%if sessions:
<table class="sessions">
  <tbody><tr><th>sessions</th><th></th><th></th></tr>
%end # if sessions
%for sess in sessions:
  <tr>
    <td title="{{ sess["name"] }}">{{ sess["name"] }}:</td>
%    if sess["count"]:
    <td><a href="{{ get_url("/sessions/<session>", session=sess["id"]) }}#{{ sess["count"] }}">{{ "{:,}".format(sess["count"]) }}</a></td>
%    else:
    <td>0</td>
%    end # if sess["count"]
    <td>from {{ format_stamp(sess["start"]) }} {{ "to %s" % format_stamp(sess["end"]) if sess["end"] else "" }}</td>
  </tr>
%end # for sess
%if sessions:
  </tbody>
</table>
%end # if sessions
</div>
