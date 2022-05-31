"""
Main script to run the ablation studies.
"""
import argparse
import os

import plix.helpers.common_functions as cf
from evaluation.ablation_evaluator import AblationEvaluator
from plix.pipeline import timer

parser = argparse.ArgumentParser(description="Commandline tool perform PLIX' ablation studies")

parser.add_argument('--ds_path', type=str,
                    default='..\\..\\arttabgen\\out\\ArtTabGen_StarSensor',
                    help='input path to the ArtTabGen dataset')
parser.add_argument('--onto_file', type=str,
                    default="data\\star-sensor.ttl",
                    help='path to the ontology')
parser.add_argument('--norm_onto_file', type=str,
                    default="data\\star-sensor_normalized.ttl",
                    help='path to the normalized ontology')
parser.add_argument('--core_onto_file', type=str,
                    default="data\\core.ttl",
                    help='path to the core ontology')
parser.add_argument('--norm_core_onto_file', type=str,
                    default="data\\core_normalized.ttl",
                    help='path to the core ontology')
parser.add_argument('--om_path', type=str,
                    default="data\\om-2.0.rdf",
                    help='path to the Ontology of units of Measure, needed for non-normalized ontologies with units.')
parser.add_argument("--studies", type=list, default=["n", "e", "u", "s"],
                    help='Available evaluation methods (need to be passed as list of strings): '
                         '[c]omparison full plix, [n]ormalization, [p]attern matches, [e]xactness, [u]nit check,'
                         '[s]ynonyms')


@timer
def main():
    args = parser.parse_args()
    cf.init_logging(logfile=os.path.join(args.ds_path, "ablation_log.txt"), do_print=True)
    gt_path = os.path.join(args.ds_path, "gt_csv")
    art_path = os.path.join(args.ds_path, "tables_csv")
    evaluator = AblationEvaluator(args, gt_path, art_path)
    evaluator.do_ablation_studies()


if __name__ == '__main__':
    main()
