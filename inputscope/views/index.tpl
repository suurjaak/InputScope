%"""
Index page.

Template arguments:
  stats      data statistics as {input: {count, first, last}}
  sessions   sessions statistics, as [{name, start, end, ..category counts}]

@author      Erki Suurjaak
@created     07.04.2015
@modified    17.10.2021
%"""
%import datetime
%from inputscope import conf
%from inputscope.util import stamp_to_date
%WEBROOT = get_url("/")
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

%if sessions:
  <tbody><tr><th>sessions</th><th></th><th></th></tr>
%end # if sessions
%for session in sessions:
  <tr>
    <td>{{ session["name"] }}:</td>
%    count = sum(session[k] for _, kk in conf.InputTables for k in kk)
%    if count:
    <td><a href="{{ get_url("/sessions/<session>", session=session["id"]) }}#{{ count }}">{{ "{:,}".format(count) }}</a></td>
    <td>from {{ stamp_to_date(session["start"]) }} {{ "to %s" % stamp_to_date(session["end"]) if session["end"] else "" }}</td>
%    else:
    <td>0</td>
%    end # if count
  </tr>
%end # for session
%if sessions:
  </tbody>
%end # if sessions
</table>
</div>
