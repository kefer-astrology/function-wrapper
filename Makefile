.PHONY: docs-env docs

docs-env:
	python -m venv docenv && \
	source docenv/bin/activate && \
	pip install -r docs/requirements.txt

docs:
	./docenv/bin/python scripts/gen_mermaid.py
	make -C docs html

run_tests:
    python -m unittest discover .
