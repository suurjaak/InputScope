/**
 * Site JavaScript.
 *
 * @author      Erki Suurjaak
 * @created     26.07.2023
 * @modified    31.07.2023
 */


/**
 * Initializes application filter elements.
 *
 * @param   base_url   base URL of current view, without application filter
 * @param   text_now   search text for current view if any
 * @param   ids_now    selected application IDs for current view if any, as comma-separated string
 * @param   selectors  map of {form,search,toggle,clear: query selector}, defaults to
 *                     {form: "#apps_form", search: "#apps_form input[type=search]",
 *                      toggle: "#apps_form_show", clear: "#apps_form_clear"}
 */
var initAppsFilter = function(base_url, text_now, ids_now, selectors) {

  var SELECTORS = {form:   "#apps_form",      search: "#apps_form input[type=search]",
                   toggle: "#apps_form_show", clear:  "#apps_form_clear"};
  Object.keys(selectors || {}).forEach(function(k) { SELECTORS[k] = selectors[k] || SELECTORS[k]; });

  var elm_apps        = document.querySelector(SELECTORS.form),    // Applications form
      elm_apps_search = document.querySelector(SELECTORS.search),  // Search input
      elm_apps_toggle = document.querySelector(SELECTORS.toggle),  // Open-link
      elm_apps_clear  = document.querySelector(SELECTORS.clear);   // Clear-button
  if (!elm_apps) return;

  var filterApps = function() { // Filter applications list by current search value
    filterItems(elm_apps, "tr", elm_apps_search.value, "hidden", true, "label");
  };

  elm_apps_search.addEventListener("keyup",  function() { callAfter(filterApps, event); });
  elm_apps_search.addEventListener("search", function() { callAfter(filterApps, event); });

  elm_apps.addEventListener("submit", function(evt) { // Assemble and load new URL, cancel form submit
    evt && evt.preventDefault && evt.preventDefault();

    var url = base_url;
    var text = elm_apps_search.value.trim();
    var ids = Array.prototype.map.call(elm_apps.querySelectorAll("input[type=checkbox]"), function(x) {
      return x.checked && (x.offsetParent !== null) ? x.value : null; // offsetParent is null if hidden
    }).filter(Boolean).sort(function(a, b) { return a - b; });

    if (text && (!ids.length || ids == ids_now)) url += "/app/" + text;
    else if (ids.length)                         url += "/app/id\:" + ids;

    if (url == window.location.pathname) {
      elm_apps.classList.add("hidden");
      elm_apps_toggle && elm_apps_toggle.classList.remove("hidden");
    } else window.location.href = url;
    return false;
  });

  elm_apps.addEventListener("reset", function() { // Hide form and restore original values
    elm_apps.reset();
    callAfter.map = null;
    window.setTimeout(function() {
      filterApps();
      elm_apps.classList.add("hidden");
      elm_apps_toggle && elm_apps_toggle.classList.remove("hidden");
    }, 0);
  });

  elm_apps_toggle && elm_apps_toggle.addEventListener("click", function() {
    elm_apps.classList.remove("hidden");
    elm_apps_toggle.classList.add("hidden");
    elm_apps_search.focus();
  });

  elm_apps_clear && elm_apps_clear.addEventListener("click", function() { // Clear all form inputs
    elm_apps_search.value = "";
    elm_apps.querySelectorAll("input[type=checkbox]").forEach(function(x) { x.checked = false; });
    filterApps();
  });

};


/**
 * Initializes keyboard heatmap.
 *
 * Requires the "h337" heatmap library.
 *
 * @param   positions  list of heatmap positions, as [{x, y, value, label}]
 * @param   events     list of keyboard events, as [{dt, data: [{x, y, count, key}]}]
 * @param   selectors  map of {heatmap,replay_start,replay_stop,interval,step,progress,status,
 *                             statustext,toggle_heatmap,toggle_keyboard,keyboard: query selector},
 *                     defaults to {heatmap: ".heatmap-container .heatmap", replay_start: "#replay_start",
 *                       replay_stop: "#replay_stop", interval: "#replay_interval",
 *                       step: "#replay_step", progress: "#progressbar", status: "#status",
 *                       statustext: "#statustext", toggle_heatmap: "#show_heatmap",
 *                       toggle_keyboard: "#show_keyboard", keyboard: "#keyboard"}
 */
var initKeyboardHeatmap = function(positions, events, selectors) {

  var RADIUS    = 20;
  var SELECTORS = {heatmap: ".heatmap-container .heatmap", replay_start: "#replay_start",
                   replay_stop: "#replay_stop", interval: "#replay_interval",
                   step: "#replay_step", progress: "#progressbar", status: "#status",
                   statustext: "#statustext", toggle_heatmap: "#show_heatmap",
                   toggle_keyboard: "#show_keyboard", keyboard: "#keyboard"};
  Object.keys(selectors || {}).forEach(function(k) { SELECTORS[k] = selectors[k] || SELECTORS[k]; });

  var elm_heatmap   = document.querySelector(SELECTORS.heatmap),
      elm_start     = document.querySelector(SELECTORS.replay_start),
      elm_stop      = document.querySelector(SELECTORS.replay_stop),
      elm_step      = document.querySelector(SELECTORS.step),
      elm_interval  = document.querySelector(SELECTORS.interval),
      elm_progress  = document.querySelector(SELECTORS.progress),
      elm_statusdiv = document.querySelector(SELECTORS.status),
      elm_status    = document.querySelector(SELECTORS.statustext),
      elm_show_hm   = document.querySelector(SELECTORS.toggle_heatmap),
      elm_show_kb   = document.querySelector(SELECTORS.toggle_keyboard),
      elm_keyboard  = document.querySelector(SELECTORS.keyboard);
  if (!elm_heatmap) return;

  var resumeFunc = null;
  var myHeatmap = h337.create({container: elm_heatmap, radius: RADIUS});
  if (positions.length) myHeatmap.setData({data: positions, max: positions[0].value});

  elm_show_kb && elm_show_kb.addEventListener("click", function() {
    elm_keyboard.classList[this.checked ? "remove" : "add"]("hidden");
  });

  elm_show_hm && elm_show_hm.addEventListener("click", function() {
    elm_heatmap.querySelector("canvas").classList[this.checked ? "remove" : "add"]("hidden");
  });

  positions.length && elm_start && elm_start.addEventListener("click", function() {
    if ("Replay" == elm_start.value) {
      elm_statusdiv.classList.add("playing");
      myHeatmap.setData({data: [], max: 0});
      elm_start.value = "Pause";
      replay(0);
    } else if ("Continue" != elm_start.value) {
      elm_start.value = "Continue";
    } else {
      elm_start.value = "Pause";
      resumeFunc && resumeFunc();
      resumeFunc = undefined;
    };
  });

  elm_stop && elm_stop.addEventListener("click", function() { // Restore replay form and reload heatmap
    elm_start.value = "Replay";
    elm_status.innerHTML = "<br />";
    elm_progress.style.width = 0;
    elm_statusdiv.classList.remove("playing");
    resumeFunc = undefined;
    myHeatmap.setData({data: positions, max: positions.length ? positions[0].value : 0});
  });

  var replay = function(index) { // Start populating heatmap incrementally
    if (!elm_statusdiv.classList.contains("playing")) return;

    if (index <= events.length - 1) {
      var step = parseInt(elm_step.value);
      if (step > 1) {
        index = Math.min(index + step - 1, events.length - 1);
        myHeatmap.setData({data: events.slice(0, index + 1).reduce(function(o, v) {
          o.push.apply(o, v.data); return o;
        }, []), max: 0});
      } else myHeatmap.addData(events[index].data);

      var percent = (100 * index / events.length).toFixed() + "%";
      if (index == events.length - 1) percent = "100%";
      else if ("100%" == percent && index < events.length - 1) percent = "99%";
      elm_status.innerHTML = events[index]["dt"] + " " + percent;
      elm_progress.style.width = percent;

      var interval = elm_interval.max - elm_interval.value + parseInt(elm_interval.min);
      if ("Pause" != elm_start.value)
        resumeFunc = function() { setTimeout(replay, interval, index + 1); };
      else
        setTimeout(replay, interval, index + 1);

    } else {
      myHeatmap.setData({data: positions, max: positions.length ? positions[0].value : 0});
      elm_start.value = "Replay";
      elm_statusdiv.classList.remove("playing");
    }
  };

};


/**
 * Initializes mouse heatmaps.
 *
 * Requires the "h337" heatmap library.
 *
 * @param   positions  heatmap positions, as {display index: [{x, y, value, label}], }
 * @param   events     list of mouse events, as [{x, y, display, dt}]
 * @param   selectors  map of {heatmap,replay_start,replay_stop,interval,step,progress,status,
 *                             statustext,fullscreen: query selector},
 *                     defaults to {heatmap: "heatmap-container .heatmap", replay_start: "#replay_start",
 *                       replay_stop: "#replay_stop", interval: "#replay_interval",
 *                       step: "#replay_step", progress: "#progressbar", status: "#status",
 *                       statustext: "#statustext", fullscreen: ".heatmap-container .fullscreen"}
 */
var initMouseHeatmaps = function(positions, events, selectors) {

  var RADIUS    = 10;
  var SELECTORS = {heatmap: ".heatmap-container .heatmap", replay_start: "#replay_start",
                   replay_stop: "#replay_stop", interval: "#replay_interval",
                   step: "#replay_step", progress: "#progressbar", status: "#status",
                   statustext: "#statustext", fullscreen: ".heatmap-container .fullscreen"};
  Object.keys(selectors || {}).forEach(function(k) { SELECTORS[k] = selectors[k] || SELECTORS[k]; });

  var elm_start     = document.querySelector(SELECTORS.replay_start),
      elm_stop      = document.querySelector(SELECTORS.replay_stop),
      elm_step      = document.querySelector(SELECTORS.step),
      elm_interval  = document.querySelector(SELECTORS.interval),
      elm_progress  = document.querySelector(SELECTORS.progress),
      elm_statusdiv = document.querySelector(SELECTORS.status),
      elm_status    = document.querySelector(SELECTORS.statustext);

  var replayevents = {};
  var resumeFunc = null;
  var myHeatmaps = Array.prototype.map.call(document.querySelectorAll(SELECTORS.heatmap), function(elm, display) {
    return h337.create({container: elm, radius: RADIUS});
  });

  Object.keys(positions).forEach(function(display) {
    myHeatmaps[display].setData({data: positions[display], max: positions[display].length ? positions[display][0].value : 0});
  });

  var on_fullscreen = function() { this.parentNode.previousElementSibling.requestFullscreen(); return false; };
  document.querySelectorAll(SELECTORS.fullscreen).forEach(function(elm) {
    elm.addEventListener("click", on_fullscreen);
  });

  Object.keys(positions).length && elm_start && elm_start.addEventListener("click", function() {
    if ("Replay" == elm_start.value) {
      elm_statusdiv.classList.add("playing");
      replayevents = {};
      Object.keys(myHeatmaps).forEach(function(display) {
        myHeatmaps[display].setData({data: [], max: positions[display].length ? positions[display][0].value : 0});
      });
      elm_start.value = "Pause";
      replay(0);
    } else if ("Continue" != elm_start.value) {
      elm_start.value = "Continue";
    } else {
      elm_start.value = "Pause";
      resumeFunc && resumeFunc();
      resumeFunc = undefined;
    };
  });

  elm_stop && elm_stop.addEventListener("click", function() { // Restore replay form and reload heatmaps
    elm_start.value = "Replay";
    elm_status.innerHTML = "<br />";
    elm_progress.style.width = 0;
    elm_statusdiv.classList.remove("playing");
    resumeFunc = undefined;
    replayevents = {};
    Object.keys(myHeatmaps).forEach(function(display) {
      myHeatmaps[display].setData({data: positions[display], max: positions[display].length ? positions[display][0].value : 0});
    });
  });

  var replay = function(index) { // Start populating heatmaps incrementally
    if (!elm_statusdiv.classList.contains("playing")) return;

    if (index <= events.length - 1) {
      var step = parseInt(elm_step.value);
      if (step > 1) {
        var index2 = Math.min(index + step - 1, events.length - 1);
        var changeds = {}; // {display index: true}
        for (var i = index; i <= index2; i++) {
          var evt = events[i];
          changeds[evt.display] = true;
          (replayevents[evt.display] = replayevents[evt.display] || []).push(evt);
        };
        index = index2;
        Object.keys(changeds).forEach(function(display) {
          myHeatmaps[display].setData({data: replayevents[display], max: 0});
        });
      } else {
        myHeatmaps[events[index].display].addData(events[index]);
        (replayevents[events[index].display] = replayevents[events[index].display] || []).push(events[index]);
      };

      var percent = (100 * index / events.length).toFixed() + "%";
      if (index == events.length - 1) percent = "100%";
      else if ("100%" == percent && index < events.length - 1) percent = "99%";
      elm_status.innerHTML = events[index]["dt"] + " " + percent;
      elm_progress.style.width = percent;

      var interval = elm_interval.max - elm_interval.value + parseInt(elm_interval.min);
      if ("Pause" != elm_start.value)
        resumeFunc = function() { setTimeout(replay, interval, index + 1); };
      else
        setTimeout(replay, interval, index + 1);

    } else {
      elm_start.value = "Replay";
      elm_statusdiv.classList.remove("playing");
      replayevents = {};
    }
  };

};


/**
 * Initializes elements to toggle element parent style on click.
 *
 * @param   selector  element selector like "a.toggle"
 * @param   style     CSS class to toggle on parent, like "collapsed"
 * @param   labels    content to swap on element, defaults to {true: "+", false: "&ndash;"}
 */
var initToggles = function(selector, style, labels) {
  var LABELS = {true: "+", false: "&ndash;"};
  Object.keys(labels || {}).forEach(function(k) { LABELS[k] = labels[k] || LABELS[k]; });
  document.querySelectorAll(selector).forEach(function(elm) {
    elm.addEventListener("click", function() {
      this.parentNode.classList.toggle(style);
      this.innerHTML = LABELS[this.parentNode.classList.contains(style)];
    });
  });
};


/**
 * Calls function after a delay, waiting until no more interaction with event target input.

 * @param   callable  function to invoke
 * @param   evt       event from input control
 * @param   delay     milliseconds to wait before calling function, defaults to 200
 */
var callAfter = function(callable, evt, delay) {
  delay = (delay == null) ? 200 : delay;
  var elem = evt.target;
  var map = callAfter.map = callAfter.map || new Map(); // {evt target: {value, timer}}
  if (!map.has(elem)) map.set(elem, {});
  var state = map.get(elem);
  window.clearTimeout(state.timer); // Avoid reacting to rapid changes

  var value = elem.value.trim();
  if (27 == evt.keyCode && "search" == elem.type) value = elem.value = "";  // Clear input on Esc
  var timer = state.timer = window.setTimeout(function() {
    if (timer == state.timer && value != state.value) {
      state.value = value;
      callable();
    };
    state.timer = null;
  }, delay);
};


/**
 * Applies text filter on items of specified element.
 *
 * @param   elem          element root or selector like "table.reports"
 * @param   selector      child element selector to filter content in, like "tbody > tr"
 * @param   text          text to filter by, item matches if containing all words and quoted phrases
 * @param   style         CSS class to add to non-matched items
 * @param   inclusive     whether search is inclusive (item matches if any word or phrase matches)
 * @param   textselector  item child selector to choose text from if not entire item, like "label"
 */
var filterItems = function(elem, selector, text, style, inclusive, textselector) {
  var words = String(text).match(/"[^"]+"|\S+/g) || [];
  words = words.map(function(w) { return w.match(/"[^"]+"/) ? w.slice(1, -1) : w });
  var regexes = words.map(function(w) { return new RegExp(escapeRegExp(w), "i"); });
  var root = (elem instanceof Element) ? elem : document.querySelector(elem);
  var itemlist = root.querySelectorAll(selector);
  for (var i = 0, ll = itemlist.length; i < ll; i++) {
    var item = itemlist[i];
    var itemtext = (textselector ? item.querySelector(textselector) : item).innerText;
    var matcher = regexes.length && itemtext.match.bind(itemtext);
    var show = !regexes.length || regexes[inclusive ? "some" : "every"](matcher);
    item.classList[show ? "remove" : "add"](style);
  };
};


/** Escapes special characters in a string for RegExp. */
var escapeRegExp = function(string) {
  return string.replace(/[\\^$.|?*+()[{]/g, "\\$&");
};
