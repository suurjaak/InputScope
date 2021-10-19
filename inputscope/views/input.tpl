%"""
Index page.

Template arguments:
  stats      data statistics as {"count": int, "periods": [{"period", "count", "class"}]}
  session    session data, if any
  sessions   sessions statistics, as [{name, start, end, ..category counts}]
  input      "mouse"|"keyboard"

@author      Erki Suurjaak
@created     07.04.2015
@modified    17.10.2021
%"""
%from inputscope import conf
%from inputscope.util import stamp_to_date
%WEBROOT = get_url("/")
%INPUTURL, URLARGS = ("/<input>", dict(input=input))
%if get("session"):
%    INPUTURL, URLARGS = "/sessions/<session>" + INPUTURL, dict(URLARGS, session=session["id"])
%end # if get("session")
%title = input.capitalize()
%rebase("base.tpl", **locals())

<div>
<table class="input_index">
%for table, data in stats.items():
%    if not data["count"]:
%        continue # for table, data
%    end # if not data["count"]
%    input = "keyboard" if table in ("keys", "combos") else "mouse"
  <tbody>
  <tr><th>{{ table }}</th></tr>
  <tr><td>Total:</td><td><a href="{{ get_url("%s/<table>" % INPUTURL, table=table, **URLARGS) }}#{{ data["count"] }}">{{ "{:,}".format(data["count"]) }}</a></td></tr>
  <tr><td>Days:</td>
    <td id="{{ table }}_periods" class="periods">
    <a href="javascript:;" class="toggle" data-input="{{ table }}" title="Toggle days">&ndash;</a>
    <div class="count">{{ len([v for v in data["periods"] if "day" == v["class"]]) }}</div>
    <div class="periods">
%    for item in data["periods"]:
      <a class="{{ item["class"] }}" href="{{ get_url("%s/<table>/<period>" % INPUTURL, table=table, period=item["period"], **URLARGS) }}#{{ item["count"] }}">{{ item["period"] }}</a>
      <span>({{ "{:,}".format(item["count"])  }})</span><br />
%    end # for item
    </div>
    </td>
  </tr>
  </tbody>
%end # for table, data

%headered = False
%for sess in sessions:
%    if not sess["count"]:
%        continue # for sess
%    end # if not sess["count"]
%    if not headered:
    <tbody><tr><th>sessions</th><th></th><th></th></tr>
%    end # if sessions
%    headered = True
  <tr>
    <td>{{ sess["name"] }}:</td>
    <td><a href="{{ get_url("/sessions/<session>/<input>", session=sess["id"], input=input) }}#{{ sess["count"] }}">{{ "{:,}".format(sess["count"]) }}</a></td>
    <td>from {{ stamp_to_date(sess["start"]) }} {{ "to %s" % stamp_to_date(sess["end"]) if sess["end"] else "" }}</td>
  </tr>
%end # for sess
%    if headered:
    </tbody>
%    end # if headered
</table>
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
