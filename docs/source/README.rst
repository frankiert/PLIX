Installation Instructions & README
**********************************

PLIX (Pipeline for Information Extraction) is a Python package and command line tool for information extraction from (PDF) documents.
As of now, it provides functionality to extract all raw data from PDFs and then extract key-value-unit tuples from it.


Setup
=====

Windows only:

For Tesseract-OCR, please download a setup binary file and install to `libs/Tesseract-OCR` or any other folder of your liking.
Please specify the path to the `.exe` in the config object.

Usage as Python Package
-----------------------

Make sure you have Python 3.8 or higher and the associated pip installed. Download the coden and install PLIX via pip (optionally in a virtual environment)::

	bash
	$ python3 -m venv plix_env         # optional
	$ source plix_env/bin/active           # optional
	$ pip install --upgrade pip
	$ cd /folder/to/plix
	$ pip install -e .

PLIX can now be imported via::

	$ python
	$ import plix
	$ from plix import Pipeline, Config


Usage examples
---------------
See the folder `example` for several usage scripts.


Additional Linux Dependencies
-----------------------------

Installing Pattern via pip might require further dependencies (mysqlclient-dev and python-dev packages).
To solve local dependency issues::

  $ sudo apt install default-libmysqlclient-dev
  $ sudo apt install python3.8-dev




Invocation
==========

To test the whole toolchain run::

	bash
	$ python3 example/pipeline_main.py


The results will be saved in the `example/data/output` folder.
Output
======

The process creates multiple files. The files are caches to skip parts of the pipeline in future runs.

In `src/plix/config.py`, the paths and names for the individual outputs can be changed.

If you do not wish to save intermediate files and just save the final result, set `save_intermediate_results` to false.


Documentation
=============
If you install PLIX locally, you can generate a documentation with `sphinx`::

    bash
    $ pip install sphinx
    $ cd docs/
    $ sphinx-build -b html source/ build/

Copyright and License
=====================

Copyright 2022 Deutsches Zentrum fuer Luft- und Raumfahrt / German Aerospace Center (DLR)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Contributors
============
Sarah Boening

Kobkaew Opasjumruskit

Christian Kiesewetter


Citation
========
To cite this software, please use the information given in `CITATION.cff`.

Dependencies
============
PLIX uses Camelot-py for table extraction from pdfs.
Version 0.9.0 or any later backwards compatible version is required.
Camelot-py is published under an MIT License and can be obtained from https://pypi.org/project/camelot-py/ .

PLIX uses ftfy for unicode string correction.
Version 6.0.3 or any later backwards compatible version is required.
Flask is published under an MIT license and can be obtained from https://pypi.org/project/ftfy/ .

PLIX uses NLTK for natural language processing.
Version 3.6.7 or any later backwards compatible version is required.
NLTK is published under an Apache License, Version 2.0 and can be obtained from https://pypi.org/project/nltk/ .

PLIX uses NumPy for mathematical operations.
Version 1.20.3 or any later backwards compatible version is required.
NumPy is published under an OSI Approved License and can be obtained from https://pypi.org/project/numpy/ .

PLIX uses opencv-python for image analysis.
Version 4.5.5.62 or any later backwards compatible version is required.
Opencv-python is published under an MIT License and can be obtained from https://pypi.org/project/opencv-python/ .

PLIX uses pandas for creating data structures.
Version 1.2.5 or any later backwards compatible version is required.
pandas is published under a BSD license and can be obtained from https://pypi.org/project/pandas/ .

PLIX uses Pattern for word singularization.
Version 3.6 or any later backwards compatible version is required.
Pattern is published under a BSD License and can be obtained from https://pypi.org/project/Pattern/ .

PLIX uses pdf2image for pdf to image conversion.
Version 1.16.1 or any later backwards compatible version is required.
pdf2image is published under an MIT License and can be obtained from https://pypi.org/project/pdf2image/ .

PLIX uses PDFMiner for extracting data from PDF documents.
Version 20211012 or any later backwards compatible version is required.
PDFMiner is published under an MIT license and can be obtained from https://pypi.org/project/pdfminer.six/ .

PLIX uses Pillow for loading images.
Version 8.0.1 or any later backwards compatible version is required.
Pillow is published under a Historical Permission Notice and Disclaimer license and can be obtained from https://pypi.org/project/Pillow/ .

PLIX uses Pint for unit conversions.
Version 0.18 or any later backwards compatible version is required.
Pint is published under an MIT license and can be obtained from https://pypi.org/project/Pint/ .

PLIX uses pyspelllchecker for spellchecking.
Version 0.5.4 or any later backwards compatible version is required.
Pyspelllchecker is published under an OSI Approved, MIT license and can be obtained from https://pypi.org/project/pyspelllchecker/ .

PLIX uses pytesseract for OCR.
Version 0.3.8 or any later backwards compatible version is required.
Pytesseract is published under an Apache License, Version 2.0 and can be obtained from https://pypi.org/project/pytesseract/ .

PLIX uses RDFLib to handle data in the RDF format.
Version 6.1.1 or any later backwards compatible version is required.
RDFLib is published under a BSD license and can be obtained from https://pypi.org/project/rdflib/ .

PLIX uses Setuptools for packaging handling.
Version 41.0.2 or any later backwards compatible version is required.
Setuptools is published under an MIT license and can be obtained from https://pypi.org/project/setuptools/ .

PLIX uses text-unidecode for replacing unicode symbols.
Version 1.3 or any later backwards compatible version is required.
text-unidecode is published under an artistic license and can be obtained from https://pypi.org/project/text-unidecode/ .

PLIX uses validators for URL validation.
Version 0.18.1 or any later backwards compatible version is required.
Validators is published under an MIT license and can be obtained from https://pypi.org/project/validators/ .
