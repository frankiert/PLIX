"""
Main script running all ArtTabGen evaluations
"""
import argparse
import os

import plix.helpers.common_functions as cf
from evaluation.arttabgen_evaluator import ArtTabGenEvaluator
from plix.pipeline import timer

parser = argparse.ArgumentParser(description="Commandline tool to benchmark different methods with ArtTabGen tables")

parser.add_argument('--arttab_path', type=str,
                    default='..\\..\\arttabgen\\out\\ArtTabGen_Motor',
                    help='input path to the ArtTabGen dataset')
parser.add_argument('--onto_file', type=str,
                    default="data\\motor_normalized.ttl",
                    help='path to the ontology')
parser.add_argument('--core_onto_file', type=str,
                    default="",
                    help='path to the core ontology')
parser.add_argument("--evaluations", type=list, default=["plix"],
                    help='Available evaluation methods (need to be passed as list of strings): '
                         '["spacy_simple_row", "spacy_simple_row_units", "spacy_ex_row", "spacy_ex_row_units", '
                         '"plix", "plix_pivot"]')


@timer
def main():
    args = parser.parse_args()
    cf.init_logging(logfile=os.path.join(args.arttab_path, "eval_log.txt"), do_print=True)
    gt_path = os.path.join(args.arttab_path, "gt_csv")
    art_path = os.path.join(args.arttab_path, "tables_csv")
    evaluator = ArtTabGenEvaluator(args, gt_path, art_path)
    evaluator.evaluate_kvu_extraction_tables()


if __name__ == '__main__':
    main()
