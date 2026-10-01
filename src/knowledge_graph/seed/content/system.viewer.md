# Graph viewer

```powershell
knowledge-graph gui
knowledge-graph gui --port 8766 --no-browser
knowledge-graph --lang ru gui
```

`serve` is a compatible alias. The default URL is `http://127.0.0.1:8765/`; the server binds only to loopback. Ctrl+C stops it. Packaged HTML, CSS and JavaScript are loaded through resources and work outside the source checkout.

Select nodes from the list or graph, read documents and follow explained connections. Search uses the chosen language. Back and forward use browser history. Copy ID gives an identifier for `node ID`. Filter node and relationship types; choose bounded neighborhood depth or the whole graph. Wheel or buttons zoom, dragging pans, and Fit centers the graph. Canvas and SVG dimensions remain bounded during resizing.

The first opening defaults to EN independently of system language. EN/RU remembers the choice in browser storage while preserving the selected node and graph settings. Explicit `--lang ru gui` opens Russian. Untranslated custom nodes retain original text. No external translation service is used.

Markdown uses safe DOM elements; raw HTML stays text. Only known graph links and HTTP/HTTPS links are clickable. The server exposes read-only API endpoints and fixed assets, not arbitrary files. Edit through a text editor and reload after validation.
