# helpers for packaging. Assumes a py3 pyvenv is active.

develop:
	python setup.py develop

sdist:
	python setup.py sdist
	ls -l dist
	tar tzf dist/awsmfa-`cat awsmfa/_version.py | head -1 | cut -f4 -d\"`.tar.gz

upload:
	python setup.py sdist upload
