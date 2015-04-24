%"""
Index page.

Template arguments:
  apptitle   program title
  stats      data statistics
  input      "mouse"|"keyboard"

@author      Erki Suurjaak
@created     07.04.2015
@modified    07.04.2015
%"""
%WEBROOT = get_url("/")
%title = input.capitalize()
%rebase("base.tpl", **locals())

<div>
<table>
%for table, data in stats.items():
    %input = "keyboard" if table in ("keys", "combos") else "mouse"
  <tbody>
  <tr><th>{{table}}</th></tr>
    %if not data["total"]:
  <tr><td>Total:</td><td>0</td></tr>
  </tbody>
        %continue # for table, data
    %end # if not data["total"]
  <tr><td>Total:</td><td><a href="{{get_url("/%s/<table>" % input, table=table)}}">{{data["total"]}}</a></td></tr>
  <tr><td>Days:</td>
    <td>
    %for item in data["days"]:
    <a href="{{get_url("/%s/<table>/<day>" % input, table=table, day=item["day"])}}">{{item["day"]}}</a> ({{item["total"]}})<br />
    %end # for item
    </td>
  </tr>
  </tbody>
%end # for table, data
</table>
</div>