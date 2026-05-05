# SPDX-License-Identifier: GPL-2.0-or-later
HERE	:=	$(shell pwd)
ifneq (, $(wildcard /usr/bin/python3))
	PYTHON = python3
else
	PYTHON = python2
endif
PACKAGE :=	rteval
VERSION :=      $(shell $(PYTHON) -c "from rteval import RTEVAL_VERSION; print(RTEVAL_VERSION)")
D	:=	10

DESTDIR	:=
PREFIX  :=      /usr
DATADIR	:=	$(DESTDIR)/$(PREFIX)/share
LOADDIR	:=	loadsource

KLOAD	:=	$(LOADDIR)/linux-6.17.7.tar.xz
BLOAD	:=	$(LOADDIR)/dbench-4.0.tar.gz
LOADS	:=	$(KLOAD) $(BLOAD)

e2e-tests: rteval-cmd
	PYTHON="$(PYTHON)" RTEVAL="$(HERE)/rteval-cmd" RTEVAL_PKG="$(HERE)" prove -o -f -v tests/e2e/

regression-tests:
	@echo "Running regression tests for measurement module error handling (RHEL-140898)"
	@echo "These tests require root privileges to replace system binaries temporarily"
	@echo ""
	@if [ "$$(id -u)" != "0" ]; then \
		echo "ERROR: regression-tests must be run as root"; \
		echo "Usage: sudo make regression-tests"; \
		exit 1; \
	fi
	./tests/regression/test-timerlat-error-handling.sh
	./tests/regression/test-cyclictest-error-handling.sh

runit:
	[ -d $(HERE)/run ] || mkdir run
	$(PYTHON) rteval-cmd -D -L -v --workdir=$(HERE)/run --loaddir=$(HERE)/loadsource --duration=$(D) -f $(HERE)/rteval.conf -i $(HERE)/rteval $(EXTRA)

load:
	[ -d ./run ] || mkdir run
	$(PYTHON) rteval-cmd --onlyload -D -L -v --workdir=./run --loaddir=$(HERE)/loadsource -f $(HERE)/rteval/rteval.conf -i $(HERE)/rteval

sysreport:
	[ -d $(HERE)/run ] || mkdir run
	$(PYTHON) rteval-cmd -D -v --workdir=$(HERE)/run --loaddir=$(HERE)/loadsource --duration=$(D) -i $(HERE)/rteval --sysreport

unit-tests:
	@echo "Running unit tests..."
	./run_tests.sh

tests: unit-tests

clean:
	rm -f *~ rteval/*~ rteval/*.py[co] *.tar.bz2 *.tar.gz doc/*~
	rm -rf rteval-[0-9]*-[0-9]*

realclean: clean
	rm -rf run

install: install_loads install_rteval

install_rteval: installdirs
	if [ "$(DESTDIR)" = "" ]; then \
		$(PYTHON) setup.py install; \
	else \
		$(PYTHON) setup.py install --root=$(DESTDIR); \
	fi

install_loads:	$(LOADS)
	[ -d $(DATADIR)/rteval/loadsource ] || mkdir -p $(DATADIR)/rteval/loadsource
	for l in $(LOADS); do \
		install -m 644 $$l $(DATADIR)/rteval/loadsource; \
	done

installdirs:
	[ -d $(DATADIR)/rteval ] || mkdir -p $(DATADIR)/rteval

tarfile: rteval-$(VERSION).tar.bz2

rteval-$(VERSION).tar.bz2:
	$(PYTHON) setup.py sdist --formats=bztar --owner root --group root
	mv dist/rteval-$(VERSION).tar.bz2 .
	rmdir dist

help:
	@echo ""
	@echo "rteval Makefile targets:"
	@echo ""
	@echo "        runit:            do a short testrun locally [default]"
	@echo "        tests:            run unit tests (alias for unit-tests)"
	@echo "        unit-tests:       run unit tests"
	@echo "        e2e-tests:        run end-to-end tests"
	@echo "        regression-tests: run regression tests for measurement modules (requires root)"
	@echo "        tarfile:          create the source tarball"
	@echo "        install:          install rteval locally"
	@echo "        clean:            cleanup generated files"
	@echo "        realclean:        Same as clean plus directory run"
	@echo "        sysreport:        do a short testrun and generate sysreport data"
	@echo "        tags:             generate a ctags file"
	@echo "        cleantags:        remove the ctags file"
	@echo ""

.PHONY: tags
tags:
	ctags -R --extra=+fq --python-kinds=+cfmvi rteval-cmd rteval

.PHONY: cleantags
cleantags:
	rm -f tags

.PHONY: tests unit-tests e2e-tests regression-tests
