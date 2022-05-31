"""
Class for AblationEvaluator.
"""

import os

import arttabgen_evaluator as ae
import plix.helpers.common_functions as cf
import plix_evaluation
import plix_evaluation as pe
from plix.pipeline import timer


class AblationEvaluator(object):
    def __init__(self, args, gt_path, ds_path):

        self.study_methods = {"c": self.full_plix_run,
                              "n": self.study_normalization,
                              "p": self.study_pattern_search,
                              "e": self.study_match_exactness,
                              "u": self.study_unit_check,
                              "s": self.study_synonym_search
                              }
        self.studies = self.validate_study_methods(args.studies)
        self.ds_path = args.ds_path
        self.ontology_file = args.onto_file
        self.norm_onto_file = args.norm_onto_file
        if args.core_onto_file:
            self.core_onto_file = args.core_onto_file
            self.norm_core_onto_file = args.norm_core_onto_file
        else:
            self.core_onto_file = None
            self.norm_core_onto_file = None
        self.om_path = args.om_path
        self.gt_path = gt_path
        self.tables_csv_path = ds_path
        self.tables = None
        self.norm_tables = None
        self.ground_truth = None
        self.keys = None
        self.norm_keys = None
        self.units = None
        self.norm_units = None
        self.total_gt_number = 0
        self.norm_total_gt_number = 0
        self.row_count = 0
        self.norm_row_count = 0
        self.gt_entries = []
        self.norm_gt_entries = []

        self.prepare_data()

    def prepare_data(self):
        self.tables = ae.load_tables(self.tables_csv_path)
        self.ground_truth = ae.load_tables(self.gt_path)
        self.keys, self.units = ae.load_ontos(self.ontology_file, self.core_onto_file, False, self.om_path)
        self.norm_keys, self.norm_units = ae.load_ontos(self.norm_onto_file, self.norm_core_onto_file, True)
        self.tables, self.ground_truth = pe.normalize_input(self.tables, self.ground_truth, self.norm_keys)
        self.total_gt_number, self.row_count, self.gt_entries = ae.prepare_gt(self.ground_truth, normalized=False)
        self.norm_total_gt_number, self.norm_row_count, self.norm_gt_entries = ae.prepare_gt(self.ground_truth,
                                                                                             normalized=True)
        self.print_gt_statistics()

    def print_gt_statistics(self):
        cf.log("the ground truth contains {} KVU tuples".format(self.norm_total_gt_number))
        cf.log("GT: positives: {}, negatives: {}, total/# rows: {}".format(self.norm_total_gt_number,
                                                                           self.norm_row_count - self.norm_total_gt_number,
                                                                           self.norm_row_count))

    def validate_study_methods(self, study_list):
        for study in study_list:
            if study not in self.study_methods.keys():
                raise ValueError("Wrong study method: " + study)
        return study_list

    def full_plix_run(self):
        study_results = []
        results = plix_evaluation.extract_kvu(self.tables, self.norm_keys, self.norm_units)
        study_results.append(plix_evaluation.format_results(results))
        return study_results

    @timer
    def study_normalization(self):
        study_results = []
        # 1. No normalized input
        results = plix_evaluation.extract_kvu(self.tables, self.keys, self.units, normalized_input=False)
        study_results.append(plix_evaluation.format_results(results))
        return study_results

    @timer
    def study_match_exactness(self):
        study_results = []
        # 1. Lev dist = 0 has to be exact match
        results = plix_evaluation.extract_kvu(self.tables, self.norm_keys, self.norm_units, lev_dist=0)
        study_results.append(plix_evaluation.format_results(results))
        # 2. Lev dist = 2
        results = plix_evaluation.extract_kvu(self.tables, self.norm_keys, self.norm_units, lev_dist=2)
        study_results.append(plix_evaluation.format_results(results))
        return study_results

    @timer
    def study_unit_check(self):
        study_results = []
        # 1. no unit check, but we allow check for if_unit_required
        results = plix_evaluation.extract_kvu(self.tables, self.norm_keys, self.norm_units, unit_check=False)
        study_results.append(plix_evaluation.format_results(results))
        return study_results

    @timer
    def study_synonym_search(self):
        study_results = []
        # 1. no check for synonyms, just looks for main key
        results = plix_evaluation.extract_kvu(self.tables, self.norm_keys, self.norm_units, use_synonyms=False)
        study_results.append(plix_evaluation.format_results(results))
        return study_results

    @timer
    def study_pattern_search(self):
        study_results = []
        # 2. do pivot
        results = plix_evaluation.extract_kvu(self.tables, self.norm_keys, self.norm_units, pivot=True)
        study_results.append(plix_evaluation.format_results(results))
        return study_results

    def do_ablation_studies(self):
        """
        run all studies defined in args.studies sequentially.
        """
        for study in self.studies:
            # extract kvu tuples
            extraction_results = self.study_methods[study]()

            # for some studies, more than one result is returned (e.g. match exactness)
            for i, results in enumerate(extraction_results):
                # check if normalized data is needed or not
                normalized = False if (study == "n" and i == 0) else True
                if normalized:
                    row_count = self.norm_row_count
                    gt_entries = self.norm_gt_entries
                else:
                    row_count = self.row_count
                    gt_entries = self.gt_entries

                ae.print_extraction_stats(len(results), row_count)
                # calculation of evaluation metrics
                study_number = str(i + 1)
                # find everything that's in the ground truth and was / wasn't found
                gt_matches, gt_match_count, gt_misses = ae.find_misses(gt_entries, results)
                # find everything that's found in the extraction and is / isn't in the ground truth
                kvu_matches, kvu_match_count, kvu_misses = ae.find_misses(results, gt_entries)
                self.save_misses(gt_misses, "in_gt_but_not_found", study, study_number)
                self.save_misses(kvu_misses, "found_but_not_in_gt", study, study_number)
                # metrics
                false_negatives, false_positives, true_positives, true_negatives = ae.calculate_pos_and_neg(
                    len(kvu_misses),
                    len(gt_misses),
                    len(results),
                    kvu_match_count,
                    row_count)
                metrics_results = ae.calculate_metrics(true_positives, true_negatives, false_positives, false_negatives)
                # save to file
                self.save_results(metrics_results, study, study_number, do_print=True)

    def save_results(self, results, method_name, number, do_print=False):
        """
        saves the calculated metrics to a file
        """
        results_file = os.path.join(self.ds_path, "results_ablation_study" + "_" + method_name + "_" + number + ".txt")
        result_str = ""
        for metric, value in results.items():
            result_str += "{}: {:.4f}\n".format(metric, value)
        if do_print:
            cf.log(result_str)
        with open(results_file, 'w+', encoding='utf-8') as f:
            f.write(result_str)

    def save_misses(self, misses, misses_name, method_name, number):
        """
        prints to all tuples that weren't found or were found extra to a file
        """
        misses_file = os.path.join(self.ds_path,
                                   "ablation_study" + "_" + misses_name + "_" + method_name + "_" + number +
                                   ".txt")
        with open(misses_file, "w+") as f:
            for row in misses:
                f.write("{}\n".format(str(row)))
