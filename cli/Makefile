# We avoid $(CURDIR) because it spits out /cygdrive/c/... on Windows Cygwin
# installs and leads to things that don't work.
VIRTUAL_ENV = venv
PYTHON3 ?= python3
PATH := $(VIRTUAL_ENV)/bin:$(VIRTUAL_ENV)/Scripts:$(PATH)

release: venv
	python setup.py sdist bdist_wheel

lint: venv
	pwd
	ls -l $(VIRTUAL_ENV)
	ls -l $(VIRTUAL_ENV)/bin
	echo $(PATH)
	which python
	@$(VIRTUAL_ENV)/bin/flake8 --exclude $(VIRTUAL_ENV) .

test: venv
	@$(VIRTUAL_ENV)/bin/pytest fathom_web/test

clean:
	rm -rf $(VIRTUAL_ENV)

venv: $(VIRTUAL_ENV)/pyvenv.cfg


# Private targets:

# Make a virtualenv at $VIRTUAL_ENV if there isn't one or if requirements have
# changed. Install the dev requirements and the actual requirements.
$(VIRTUAL_ENV)/pyvenv.cfg: dev-requirements.txt setup.py
	$(PYTHON3) -m venv $(VIRTUAL_ENV)
	$(PYTHON3) -m pip install -r dev-requirements.txt
	$(PYTHON3) -m pip install -e . -f https://download.pytorch.org/whl/torch_stable.html


.PHONY: release lint test clean venv
