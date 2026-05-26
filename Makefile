.PHONY: build publish clean test

build:
	python3 -m build

publish: build
	python3 -m twine upload dist/*

clean:
	rm -rf dist/ build/ *.egg-info

test:
	python3 -m unittest discover -s tests
