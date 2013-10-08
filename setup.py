from distutils.core import setup
import mboxfilter

setup(
    name = 'mboxfilter',
    version = mboxfilter.__version__,
    author = "P. Andreas Moeller",
    author_email = 'kontakt@pamoller.com',
    url = 'http://pamoller.com/mboxfilter.html',
    license = 'MIT',
    description = 'Filter and sort mails from mboxes for archiving and reporting',
    long_description = open('README.rst', 'r').read(),
    py_modules = ['mboxfilter'],
    scripts = ['bin/mboxfilter'],
    requires = ["dateutil"],
    install_requires = ["python-dateutil"],
    classifiers = [
     "Programming Language :: Python :: 2.6",
     "Programming Language :: Python :: 2.7",
     "Programming Language :: Python :: 3",
     "License :: OSI Approved :: MIT License",
     "Topic :: Communications :: Email"
    ]
)
