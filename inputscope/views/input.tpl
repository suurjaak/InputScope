%"""
Index page.

Template arguments:
  stats      data statistics as {"count": int, "periods": [{"period", "count", "class"}]}
  input      "mouse"|"keyboard"
  table      "moves"|"clicks"|"scrolls"|"keys"|"combos", if any

@author      Erki Suurjaak
@created     07.04.2015
@modified    26.01.2021
%"""
%WEBROOT = get_url("/")
%title = input.capitalize()
%rebase("base.tpl", **locals())

<div>
<table class="input_index">
%for table, data in stats.items():
    %if not data["count"]:
        %continue # for table, data
    %end # if not data["count"]
    %input = "keyboard" if table in ("keys", "combos") else "mouse"
  <tbody>
  <tr><th>{{ table }}</th></tr>
  <tr><td>Total:</td><td><a href="{{ get_url("/%s/<table>" % input, table=table) }}#{{ data["count"] }}">{{ "{:,}".format(data["count"]) }}</a></td></tr>
  <tr><td>Days:</td>
    <td id="{{ table }}_periods" class="periods">
    <a href="javascript:;" class="toggle" data-input="{{ table }}" title="Toggle days">&ndash;</a>
    <div class="count">{{ len([v for v in data["periods"] if "day" == v["class"]]) }}</div>
    <div class="periods">
    %for item in data["periods"]:
      <a class="{{ item["class"] }}" href="{{ get_url("/%s/<table>/<period>" % input, table=table, period=item["period"]) }}#{{ item["count"] }}">{{ item["period"] }}</a>
      <span>({{ "{:,}".format(item["count"])  }})</span><br />
    %end # for item
    </div>
    </td>
  </tr>
  </tbody>
%end # for table, data
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
