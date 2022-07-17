%"""
Index page.

Template arguments:
  stats      data statistics as {"count": int, "periods": [{"period", "count", "class"}]}
  session    session data, if any
  sessions   sessions statistics, as [{name, start, end, ..category counts}]
  input      "mouse"|"keyboard"

@author      Erki Suurjaak
@created     07.04.2015
@modified    16.07.2022
%"""
%from inputscope import conf
%from inputscope.util import format_stamp
%WEBROOT = get_url("/")
%INPUTURL, URLARGS = ("/<input>", dict(input=input))
%if get("session"):
%    INPUTURL, URLARGS = "/sessions/<session>" + INPUTURL, dict(URLARGS, session=session["id"])
%end # if get("session")
%title, page = input.capitalize(), "input"
%rebase("base.tpl", **locals())

<div>
<table class="totals">
%for table, data in stats.items():
%    if not data["count"]:
%        continue # for table, data
%    end # if not data["count"]
%    input = "keyboard" if table in ("keys", "combos") else "mouse"
  <tbody>
  <tr><th colspan="2">{{ table }}</th></tr>
  <tr><td>Total:</td><td><a href="{{ get_url("%s/<table>" % INPUTURL, table=table, **URLARGS) }}#{{ data["count"] }}">{{ "{:,}".format(data["count"]) }}</a></td></tr>
  <tr><td>Days:</td>
    <td id="{{ table }}_periods" class="periods">
    <a href="javascript:;" class="toggle" data-input="{{ table }}" title="Toggle days">&ndash;</a>
    <div class="count">{{ len([v for v in data["periods"] if "day" == v["class"]]) }}</div>
    <div class="periods">
%    for item in data["periods"]:
      <div class="flex-row">
        <a class="{{ item["class"] }}" href="{{ get_url("%s/<table>/<period>" % INPUTURL, table=table, period=item["period"], **URLARGS) }}#{{ item["count"] }}">{{ item["period"] }}</a>
        <span>({{ "{:,}".format(item["count"])  }})</span>
      </div>
%    end # for item
    </div>
    </td>
  </tr>
  </tbody>
%end # for table, data
</table>

%did_sessions = False
%for sess in (s for s in sessions if s["count"]):
%    if not did_sessions:
<table class="sessions">
  <tbody>
  <tr><th>sessions</th><th></th><th></th></tr>
%    end # if sessions
%    did_sessions = True
  <tr>
    <td title="{{ sess["name"] }}">{{ sess["name"] }}:</td>
    <td><a href="{{ get_url("/sessions/<session>/<input>", session=sess["id"], input=input) }}#{{ sess["count"] }}">{{ "{:,}".format(sess["count"]) }}</a></td>
    <td>from {{ format_stamp(sess["start"]) }} {{ "to %s" % format_stamp(sess["end"]) if sess["end"] else "" }}</td>
  </tr>
%end # for sess
%    if did_sessions:
  </tbody>
</table>
%    end # if did_sessions
</div>


<script type="text/javascript">
  window.addEventListener("load", function() {

      var linklist = document.getElementsByClassName("toggle");
      for (var i = 0; i < linklist.length; i++) {
        linklist[i].addEventListener("click", function() {
          var on = (this.innerText == "+");
          this.innerHTML = on ? "&ndash;" : "+";
          document.getElementById(this.dataset.input + "_periods").classList.toggle("collapsed");
        });
      };

  });
</script>
