JS := $(shell find . -name '*.mjs' | sed 's/\.mjs/\.js/')

# It's faster to invoke Babel once and compile everything than to invoke it
# separately on even 2 individual files that changed.
%.js: %.mjs; @node_modules/.bin/babel *.mjs **/*.mjs --out-dir .

all: $(JS)

lint:
	@node_modules/.bin/eslint --ext mjs .
	@node_modules/.bin/eslint test/functional

test: $(JS)
	@node_modules/.bin/mocha --recursive
	pytest cli/fathom_web/test

coverage: $(JS)
	@node_modules/.bin/istanbul cover node_modules/.bin/_mocha -- --recursive

debugtest: $(JS)
	# This is known to work on node 7.6.0.
	@node_modules/.bin/mocha --inspect-brk

publish: $(JS)
	npm publish

cli:
	cd cli && python setup.py sdist bdist_wheel

clean:
	rm -f $(JS)

.PHONY: all lint test coverage debugtest cli
