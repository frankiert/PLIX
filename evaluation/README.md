# ArtTabGen Evaluation

## Installation

If you want to run just the evaluation, follow these steps:

````commandline
pip install -r evaluation/evaluation_requirements.txt
pip install -e .
cd evaluation
````

Please download the official Ontology of units of Measure (OM) 2.0 and place it in `/data` as `om-2.0.rdf`.

## Replication of Paper Results

To replicate the results of out paper, you need to test PLIX on our `ArtTabGen` benchmarking data set from Zenodo.

Then extract it to a folder of your liking and run

````commandline
cd plix/evaluation
python arttabgen_evaluation.py --arttab_path=/path/to/arttabdomaindataset/ --onto_file=domain_ontology.ttl 
````

For the Motor set, you need `ArtTabGen_Motor` and `motor.ttl` as the `onto_file`. For the Star Sensor set, chose
`ArtTabGen_StarSensor`, `onto_file=star_sensor.ttl` and `core_onto_file=star_sensor_core.ttl`. 
