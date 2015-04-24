%"""
Index page.

Template arguments:
  apptitle   program title
  stats      data statistics

@author      Erki Suurjaak
@created     07.04.2015
@modified    07.04.2015
%"""
%WEBROOT = get_url("/")
%rebase("base.tpl", **locals())

<div>
<table>
%for input, data in stats.items():
  <tbody>
  <tr><th>{{input}}</th></tr>
    %if not data["total"]:
  <tr><td>Total:</td><td>0</td></tr>
  </tbody>
        %continue # for input, data
    %end # if not data["total"]
  <tr><td>Total:</td><td><a href="{{get_url("/<input>", input=input)}}">{{data["total"]}}</a> from {{data["first"]}} to {{data["last"]}}</td></tr>
  </tbody>
%end # for input, data
</table>
</div>
