/**
 * Shared JavaScript.
 *
 * @author      Erki Suurjaak
 * @created     26.07.2023
 * @modified    26.07.2023
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
  return string.replace(/[-[\]{}()*+!<=:?.\/\^\\$|#\s,]/g, "\\$&");
};
