# We avoid $(CURDIR) because it spits out /cygdrive/c/... on Windows Cygwin
# installs and leads to things that don't work.
VIRTUAL_ENV = ./venv
PYTHON3 ?= python3
# PATH seems to be exported even without "export", but I kept it to be explicit.
export PATH := $(VIRTUAL_ENV)/bin:$(VIRTUAL_ENV)/Scripts:../fathom/node_modules/.bin:$(PATH)

release: venv
	PATH=$(PATH) python setup.py sdist bdist_wheel

lint: venv npm_installed
	@PATH=$(PATH) flake8 --exclude $(VIRTUAL_ENV) .
	cd ../fathom && node_modules/.bin/eslint -c .eslintrc.yml ../cli/fathom_web/test/resources

test: venv npm_installed
	@PATH=$(PATH) pytest fathom_web/test

clean:
	rm -rf $(VIRTUAL_ENV)

venv: $(VIRTUAL_ENV)/pyvenv.cfg


# Private targets:

# Make a virtualenv at $VIRTUAL_ENV if there isn't one or if requirements have
# changed. Install the dev requirements and the actual requirements.
$(VIRTUAL_ENV)/pyvenv.cfg: dev-requirements.txt setup.py
	$(PYTHON3) -m venv $(VIRTUAL_ENV)
	# We don't path-qualify pip3 because python -m venv on Travis creates a
	# venv with no pip executable in it.
	PATH=$(PATH) pip3 install -r dev-requirements.txt
	PATH=$(PATH) pip3 install -e . -f https://download.pytorch.org/whl/torch_stable.html

npm_installed:
	$(MAKE) -C ../fathom .npm_installed

.PHONY: release lint test clean venv npm_installed
