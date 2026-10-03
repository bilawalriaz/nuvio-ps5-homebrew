.PHONY: build ui test check docs-check release upstream
build:
	python3 scripts/build.py
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
