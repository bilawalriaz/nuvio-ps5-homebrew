.PHONY: build ui test check docs-check release upstream feedback
LOADER_PORT ?= 9021
build:
	python3 scripts/build.py --title-ui --auto-bootstrap $(LOADER_PORT)
ui:
	python3 scripts/build.py --ui-only
test:
	python3 -m unittest discover -s tests -v
docs-check:
	python3 scripts/docs_check.py
check: test docs-check
	python3 scripts/check.py
release:
	python3 scripts/package_release.py
upstream:
	python3 scripts/update_upstreams.py
feedback:
	python3 scripts/feedback.py
.PHONY: close
close:
	python3 scripts/close.py
