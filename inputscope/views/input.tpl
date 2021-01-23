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
<table class="input_index">
%for table, data in stats.items():
    %if not data["count"]:
        %continue # for table, data
    %end # if not data["count"]
    %input = "keyboard" if table in ("keys", "combos") else "mouse"
  <tbody>
  <tr><th>{{ table }}</th></tr>
  <tr><td>Total:</td><td><a href="{{ get_url("/%s/<table>" % input, table=table) }}">{{ "{:,}".format(data["count"]) }}</a></td></tr>
  <tr><td>Days:</td>
    <td id="{{ table }}_days" class="days">
    <a href="javascript:;" class="toggle" data-input="{{ table }}" title="Toggle days">&ndash;</a>
    <div class="count">{{ len(data["days"]) }}</div>
    <div class="days">
    %for item in data["days"]:
      <a href="{{ get_url("/%s/<table>/<day>" % input, table=table, day=item["day"]) }}">{{ item["day"] }}</a> ({{ "{:,}".format(item["count"])  }})<br />
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
          document.getElementById(this.dataset.input + "_days").classList.toggle("collapsed");
        });
      };

  });
</script>
