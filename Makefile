.PHONY: run_tests docs venv venv-streamlit venv-kivy venv-docs sync-pyproject

VENV_DIR := venv
PYTHON := python3

run_tests:
	python -m unittest discover .

docs:
	@echo "Generating documentation (requires venv with all dependencies)..."
	@KIVY_NO_ARGS=1 python -m devtools.docs_export --out docs/site/content/auto --hugo
	@python -m devtools.diagram_export --out docs/site/content/models.mmd --enums-out docs/site/content/enums.md
	@echo "Documentation generated in docs/site/content/auto/ (with Hugo frontmatter), docs/site/content/models.mmd, and docs/site/content/enums.md"

venv:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/python -m pip install --upgrade pip
	$(VENV_DIR)/bin/python -m pip install -r requirements/base.txt

venv-streamlit:
	$(PYTHON) -m venv venv-streamlit
	venv-streamlit/bin/python -m pip install --upgrade pip
	venv-streamlit/bin/python -m pip install -r requirements/streamlit.txt

venv-kivy:
	$(PYTHON) -m venv venv-kivy
	venv-kivy/bin/python -m pip install --upgrade pip
	venv-kivy/bin/python -m pip install -r requirements/kivy.txt

venv-docs:
	$(PYTHON) -m venv venv-docs
	venv-docs/bin/python -m pip install --upgrade pip
	venv-docs/bin/python -m pip install --upgrade --force-reinstall -e ".[docs]"

sync-pyproject:
	$(PYTHON) -m devtools.sync_pyproject