PY ?= python3

.PHONY: test graphs check run scan install uninstall

test:
	$(PY) -m pytest -q

graphs:
	$(PY) scripts/test_graph.py
	-code-review-graph update

check: graphs

run:
	$(PY) -m mishlat

scan:
	$(PY) -m mishlat scan

install:
	./install.sh

uninstall:
	./uninstall.sh

# The plugin carries its own copy of the scanner package (no GUI modules).
plugin-sync:
	rsync -a --delete --exclude '__pycache__' --exclude 'window.py' --exclude 'app.py' --exclude 'tray.py' --exclude 'watcher.py' mishlat/ plugin/lib/mishlat/
