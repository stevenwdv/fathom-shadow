# If there's an activated virtualenv, use that. Otherwise, make one in the cwd.
VIRTUAL_ENV ?= $(PWD)/venv
PATH := $(PWD)/node_modules/geckodriver/bin:$(PATH)

JS := $(shell find . -name '*.mjs' | sed 's/\.mjs/\.js/')

# It's faster to invoke Babel once and compile everything than to invoke it
# separately on even 2 individual files that changed.
%.js: %.mjs; @node_modules/.bin/babel *.mjs **/*.mjs --out-dir .

all: $(JS)

lint: js_lint py_lint

js_lint: $(JS)
	@node_modules/.bin/eslint --ext mjs .
	@node_modules/.bin/eslint test/browser

py_lint: $(VIRTUAL_ENV)/bin/activate
	@$(VIRTUAL_ENV)/bin/flake8 cli

test: js_test py_test

# Does not include browser tests. See all_js_test target (Linux-based shells
# only).
js_test: $(JS)
	@node_modules/.bin/mocha

py_test: $(VIRTUAL_ENV)/bin/activate
	@$(VIRTUAL_ENV)/bin/pytest cli/fathom_web/test

# Run even the browser tests and the coverage report. Works only on UNIXy
# shells.
all_js_test: $(JS)
	./test/browser/start_http_server & echo "$$!" > pid
	node_modules/.bin/istanbul cover node_modules/.bin/_mocha -- --recursive
	kill $$(cat pid)
	rm pid

coveralls:
	cat ./coverage/lcov.info | coveralls

debugtest: $(JS)
	# This is known to work on node 7.6.0.
	@node_modules/.bin/mocha --inspect-brk

publish: $(JS)
	npm publish

cli:
	cd cli && python setup.py sdist bdist_wheel

clean:
	rm -rf $(JS) venv


# Private targets:

# Make a virtualenv at $VIRTUAL_ENV if there isn't one or if requirements have
# changed. Install the dev requirements and the actual requirements.
$(VIRTUAL_ENV)/bin/activate: tooling/dev-requirements.txt cli/setup.py
	python3 -m venv $(VIRTUAL_ENV)
	$(VIRTUAL_ENV)/bin/pip install -r tooling/dev-requirements.txt
	$(VIRTUAL_ENV)/bin/pip install -e cli

.PHONY: all lint js_lint py_lint test js_test py_test all_js_test coveralls debugtest publish cli clean
