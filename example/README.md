# Minimal Examples

This folder contains 3 minimal running examples for using PLIX.

## Individual Steps

If you want to run some individual steps in your own code without the whole pipeline, `example_indiv_steps.py`
demonstrates just that.

## Pipeline as a Package

If you want to run the whole pipeline within your code instead, please see `example_package.py`.

## PLIX Pipeline in the Command Line

To run the whole pipeline in the command line, you can simply execute `pipeline_main.py`.

**IMPORTANT**

Do not forget to install the dependencies into the libs/ folder!

These examples work with sample files provided in this folder. If you want to use your own, check the config parameters
beforehand and point them to your data folders.

````commandline
cd example/
python3 pipeline_main.py
````
