%"""
Index page.

Template arguments:
  stats      data statistics

@author      Erki Suurjaak
@created     07.04.2015
@modified    26.01.2021
%"""
%WEBROOT = get_url("/")
%rebase("base.tpl", **locals())

<div>
<table>
%for input, data in stats.items():
  <tbody><tr><th>{{ input }}</th><th></th><th></th></tr><tr>
  <td>Total:</td>
    %if data["count"]:
      <td><a href="{{ get_url("/<input>", input=input) }}#{{ data["count"] }}">{{ "{:,}".format(data["count"]) }}</a></td>
      <td>from {{ data["first"] }} to {{ data["last"] }}</td>
    %else:
      <td>0</td>
    %end # if data["count"]
  </tr></tbody>
%end # for input, data
</table>
</div>
