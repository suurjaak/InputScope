%"""
Index page.

Template arguments:
  stats      data statistics
  input      "mouse"|"keyboard"
  table      "moves"|"clicks"|"scrolls"|"keys"|"combos", if any

@author      Erki Suurjaak
@created     07.04.2015
@modified    20.05.2015
%"""
%WEBROOT = get_url("/")
%title = input.capitalize()
%rebase("base.tpl", **locals())

<div>
<table>
%for table, data in stats.items():
    %if not data["count"]:
        %continue # for table, data
    %end # if not data["count"]
    %input = "keyboard" if table in ("keys", "combos") else "mouse"
  <tbody>
  <tr><th>{{table}}</th></tr>
  <tr><td>Total:</td><td><a href="{{get_url("/%s/<table>" % input, table=table)}}">{{data["count"]}}</a></td></tr>
  <tr><td>Days:</td>
    <td>
    %for item in data["days"]:
    <a href="{{get_url("/%s/<table>/<day>" % input, table=table, day=item["day"])}}">{{item["day"]}}</a> ({{item["count"]}})<br />
    %end # for item
    </td>
  </tr>
  </tbody>
%end # for table, data
</table>
</div>
