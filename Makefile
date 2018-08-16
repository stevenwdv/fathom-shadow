all: commonjs

lint:
	@node_modules/.bin/eslint --ext mjs .

commonjs:
	@node_modules/.bin/babel *.mjs **/*.mjs --out-dir .

test: commonjs
	@node_modules/.bin/mocha

debugtest:
	# This is known to work on node 7.6.0.
	@node_modules/.bin/mocha --inspect --debug-brk

clean:
	rm -f clusters.js exceptions.js fnode.js index.js lhs.js optimizers.js rhs.js rule.js ruleset.js side.js utils.js utilsForBackend.js utilsForFrontend.js examples/readability.js test/clusters_tests.js test/demos.js test/lhs_tests.js test/readability_tests.js test/rhs_tests.js test/rule_tests.js test/ruleset_tests.js test/side_tests.js test/utils_tests.js

.PHONY: all lint commonjs test debugtest
