%"""
Base template, with site layout and style.

Template arguments:
  title      page title, if any
  base       main content

@author      Erki Suurjaak
@created     07.04.2015
@modified    23.04.2015
%"""
%WEBROOT = get_url("/")
<!DOCTYPE html>
<html>
<head>
  <title>{{conf.Title}}{{" - " + title if get("title") else ""}}</title>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
  <meta name="Author" content="Erki Suurjaak">
  <link rel="icon" type="image/x-icon" href="{{WEBROOT}}static/icon.ico" />
  <link rel="stylesheet" href="{{WEBROOT}}static/site.css" />
  <script src="{{WEBROOT}}static/heatmap.min.js"></script>
</head>
<body>
<div id="header">
  <a href="{{WEBROOT}}" id="indexlink">{{conf.Title}}</a>
</div>

<div id="content">
{{!base}}
</div>

<div id="footer">
<div>
  Mouse and keyboard input visualizer. &copy; 2015 Erki Suurjaak. <a href="{{conf.HomepageUrl}}" target="_blank">github</a>
</div>
</div>

</body>
</html>
