all: sdist install regress

sdist:
	python setup.py sdist
	
install:
	python setup.py install

register: regress
	python setup.py register
	
regress:
	python test/test_mboxfilter.py

upload: regress
	python setup.py upload sdist
