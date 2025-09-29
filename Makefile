# Python and pip detection - can be overridden via environment
PYTHON ?= $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python3)
PIP ?= $(shell command -v pip3 2>/dev/null || command -v pip 2>/dev/null || echo pip)

VERSION := $(shell $(PYTHON) -m 'rlc.cloud_repos' 2>/dev/null)
$(info "VERSION: $(VERSION)")

PACKAGE := rlc.cloud-repos
PY_PACKAGE := rlc.cloud_repos
RPM_PACKAGE := python3-rlc-cloud-repos
distdir := dist

.PHONY: install clean test lint format dist rpm spec dev mock test-version

test-version:
	@echo "Testing VERSION is non-empty..."
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ VERSION is empty"; \
		exit 1; \
	else \
		echo "✅ VERSION is non-empty: $(VERSION)"; \
	fi

$(distdir)/$(RPM_PACKAGE).spec: rpm/$(RPM_PACKAGE).spec.in
	@echo "📄 Generating RPM spec file..."

	mkdir -p $(distdir)
	sed -e 's/^\(Version:\s*\)VERSION/\1'$(VERSION)'/' rpm/$(RPM_PACKAGE).spec.in > $(distdir)/$(RPM_PACKAGE).spec

spec: test-version $(distdir)/$(RPM_PACKAGE).spec

dev:
	@echo "🔧 Installing development dependencies..."
	$(PIP) install $(PIP_OPTIONS) -e .[dev]
	$(PIP) install $(PIP_OPTIONS) -e ./framework[dev]

install:
	@echo "🔧 Installing $(PACKAGE) globally..."
	$(PIP) install .

$(distdir)/$(PY_PACKAGE)-$(VERSION)-py3-none-any.whl: setup.cfg setup.py MANIFEST.in $(shell find cloud-repos -name '*.py') config/* data/*
	@echo "🛞 Building wheel..."
	$(PYTHON) -m build --wheel

dist: test-version $(distdir)/$(PY_PACKAGE)-$(VERSION)-py3-none-any.whl

$(distdir)/$(PACKAGE)-$(VERSION).tar.gz: setup.cfg setup.py MANIFEST.in $(shell find cloud-repos -name '*.py') config/* data/*
	@echo "📦 Building source distribution..."
	$(PYTHON) -m build --sdist

sdist: test-version $(distdir)/$(PACKAGE)-$(VERSION).tar.gz

lint:
	@echo "🔍 Running linters..."
	black --check cloud-repos framework tests || black --diff cloud-repos framework tests
	isort --check-only cloud-repos framework tests
	flake8 cloud-repos framework tests

format:
	@echo "🎨 Formatting code..."
	black cloud-repos framework tests
	isort cloud-repos framework tests

clean:
	@echo "🦚 Cleaning build artifacts..."
	# rm -f rpm/$(RPM_PACKAGE).spec rpm/*.tar.gz
	rm -rf build dist framework/build framework/dist
	rm -rf rpm/[0-9]*.patch
	find ./ -type d -name "*.egg-info" -exec rm -rf {} +
	find ./ -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.dist-info" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.orig" -exec rm -f {} +
	find . -type f -name "*.rej" -exec rm -f {} +
	rm -rf ~/.cache/pip/wheels/*
	rm -f .coverage

rpm: spec sdist
	@echo "📄 Copying tarball into SOURCES for rpmbuild..."
	mkdir -p ~/rpmbuild/SOURCES
	cp dist/$(PACKAGE)-$(VERSION).tar.gz ~/rpmbuild/SOURCES/

	@echo "🚰 Running rpmbuild..."
	if ! rpmbuild -ba $(distdir)/$(RPM_PACKAGE).spec; then \
		echo "💥 RPM build failed. Ensure BuildRequires includes pyproject macros or fallback to pip install."; \
		exit 1; \
	fi

MOCK_CONFIG ?= rocky-8-x86_64
MOCK_OPTS ?=

# If your sdist doesn't work with these steps, stop, and fix the sdist generation (probably by downgrading setuptools and or python), unless you want to update all the CI jobs too and test thouroughly on Centos 7 and Rocky 8.
mock: test-version spec sdist
	@echo "📦 Building SRPM..."
	@echo "⚡ This may not work if you're not using python 3.6 and a fairly old SetupTools to generate the sdist."
	mkdir -p $(distdir)/rpm/{SOURCES,SPECS}
	cp $(distdir)/$(RPM_PACKAGE).spec $(distdir)/rpm/SPECS/
	cp $(distdir)/$(PACKAGE)-$(VERSION).tar.gz $(distdir)/rpm/SOURCES/
	@echo "🧪 Running mock build..."
	mock -r $(MOCK_CONFIG) $(MOCK_OPTS) --resultdir=$(distdir) --enable-network --sources $(distdir)/rpm/SOURCES --spec $(distdir)/rpm/SPECS/$(RPM_PACKAGE).spec

# Testing
PYTHONPATH := src
PYTHON_VERSION ?= 3.11

.PHONY: test test-coverage test-podman sdist-podman

sdist-podman:
	@echo "🐋 Building source distribution in Podman container with Python 3.6..."
	podman pull docker.io/library/python:3.6
	podman run --rm --security-opt label=disable -v .:/app -w /app python:3.6 bash -c "make dev && make sdist"

test-podman:
	@echo "🐋 Running tests in Podman container with Python $(PYTHON_VERSION)..."
	podman pull docker.io/library/python:$(PYTHON_VERSION)
	podman run --rm --security-opt label=disable -v .:/app -w /app python:$(PYTHON_VERSION) bash -c \
		"python -m pip install --upgrade pip setuptools && make dev && python -m pytest --cov --cov-report=term-missing"

test:
	@echo "🧪 Running test suite with pytest..."
	@PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest -v tests --cov --cov-report=term-missing

test-coverage:
	pytest --cov --cov-report=term-missing

all: clean rpm publish clean

# Include local overrides
-include Makefile.local

