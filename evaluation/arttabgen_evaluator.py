"""
Methods and class for the ArtTabGenEvaluator.
"""

import os

import pandas as pd

import evaluation.helpers.ontology_utils as ou
import plix.helpers.common_functions as cf
import plix_evaluation
from evaluation.spacy_ import spacy_simple_table_evaluation as sst, spacy_extended_row_evaluation as ser, \
    spacy_simple_row_evaluation as ssr, spacy_simple_row_units_evaluation as ssru, \
    spacy_extended_row_unit_evaluation as seru, spacy_extended_table_unit_evaluation as setu, \
    spacy_simple_table_units_evaluation as sstu, spacy_extended_table_evaluation as SET, \
    stanza_simple_unit_evaluation as SSU, stanza_extended_unit_evaluation as SEU
from plix.pipeline import timer


def calculate_metrics(true_pos, true_neg, false_pos, false_neg):
    results = {"accuracy": (true_pos + true_neg) / (true_pos + true_neg + false_pos + false_neg),
               "precision": true_pos / (true_pos + false_pos) if (true_pos + false_pos) != 0 else 0,
               "recall": true_pos / (true_pos + false_neg)}
    results["F1_Score"] = 2 * ((results["precision"] * results["recall"]) / (results["precision"] + results["recall"])
                               if (results["precision"] + results["recall"]) > 0 else 0)
    return results


def calculate_pos_and_neg(len_kvu_misses, len_gt_misses, len_extraction_results, kvu_match_count, row_count):
    false_negatives = len_gt_misses
    false_positives = len_kvu_misses
    true_positives = kvu_match_count
    true_negatives = (row_count - len_extraction_results) - false_negatives
    return false_negatives, false_positives, true_positives, true_negatives


def load_ontos(onto_file, core_onto_file, normalized, om_path=""):
    """
    loads all needed ontologies and converts them into data structures PLIX needs.
    """
    graph, classes = ou.load_ontology_classes(onto_file)
    if normalized:
        unit_onto = ou.read_classes_normalized_unit(onto_file)
    else:
        unit_onto = ou.get_classes_unit(onto_file, om_path)

    keyword_onto = ou.list_classes_labels(graph, classes, normalized)
    if core_onto_file:
        core_graph, core_classes = ou.load_ontology_classes(core_onto_file)
        if normalized:
            core_unit_onto = ou.read_classes_normalized_unit(core_onto_file)
        else:
            core_unit_onto = ou.get_classes_unit(core_onto_file, om_path)

        core_keyword_onto = ou.list_classes_labels(core_graph, core_classes, normalized)
        keyword_onto += core_keyword_onto
        unit_onto.update(core_unit_onto)
    return keyword_onto, unit_onto


def load_tables(path):
    """
    loads tables from csv files and converts them to a dataframe object.
    Can be used for ground truth and normal tables
    """
    tables = []
    file_names = []
    columns = ['Filename', 'TableData', 'NormalizedTableData']
    files = os.listdir(path)
    for file in files:
        tables_file = []
        with open(os.path.join(path, file), 'r', encoding='utf-8') as f:
            table = f.readlines()
            for i, row in enumerate(table):
                table[i] = row.replace("\n", "").split(';')
            file_names.append(file.split("_")[-1])
            tables_file.append(table)
        tables.append(tables_file)
    df = pd.DataFrame(columns=columns)
    df['Filename'] = file_names
    df['TableData'] = tables
    return df


def prepare_gt(gt, normalized=True):
    """
    takes the loaded csv files and formats them into data structure for evaluation
    """
    gt_tables = gt["NormalizedTableData"] if normalized else gt["TableData"]
    gt_file = gt["Filename"]
    count = 0
    gt_list = []
    total_row = 0
    for entry, file in zip(gt_tables, gt_file):
        for table in entry:
            for row in table:
                total_row += 1
                if len(row) >= 3 and all([True if len(word) > 0 else False for word in row[:-1]]):
                    count += 1
                    unit = ''
                    if len(row) >= 4:
                        unit = row[3]
                    gt_list.append([file, row[0], row[2], unit])
    return count, total_row, gt_list


def find_misses(table_1, table_2):
    """
    table_1 is ground truth
    table_2 is the hypothesis
    """
    match_count = 0
    all_matches = []
    all_misses = []
    checktable_2 = set([";".join([cell for cell in entry]) for entry in table_2])
    for entry in table_1:
        match_1 = ";".join([cell for cell in entry])
        if match_1 in checktable_2:
            match_count += 1
            all_matches.append(entry)
        else:
            all_misses.append(entry)
    return all_matches, match_count, all_misses


def print_extraction_stats(len_extraction_results, row_count):
    cf.log("The extraction found {} KVU tuples".format(len_extraction_results))

    cf.log("Test: positives: {}, negatives: {}, total: {}".format(len_extraction_results,
                                                                  row_count - len_extraction_results,
                                                                  row_count))


class ArtTabGenEvaluator(object):
    def __init__(self, args, gt_path, art_path):
        self.eval_methods = {"plix": self.get_plix_results,
                             "plix_pivot": self.get_plix_pivot_results,
                             "spacy_simple_table": self.get_spacy_simple_table_results,
                             "spacy_simple_row": self.get_spacy_simple_row_results,
                             "spacy_simple_row_units": self.get_spacy_row_units_results,
                             "spacy_simple_table_units": self.get_spacy_table_units_results,
                             "spacy_ex_table": self.get_spacy_ex_table_results,
                             "spacy_ex_table_units": self.get_spacy_ex_table_unit_results,
                             "spacy_ex_row": self.get_spacy_ex_row_results,
                             "spacy_ex_row_units": self.get_spacy_ex_row_unit_results,
                             "stanza_simple_units": self.get_stanza_simple_unit_results,
                             "stanza_ex_units": self.get_stanza_ex_unit_results
                             }
        self.evaluation_methods = self.validate_evaluation_methods(args.evaluations)
        self.arttab_path = args.arttab_path
        self.ontology_file = args.onto_file
        if args.core_onto_file:
            self.core_onto_file = args.core_onto_file
        else:
            self.core_onto_file = None
        self.gt_path = gt_path
        self.tables_csv_path = art_path
        self.tables = None
        self.ground_truth = None
        self.keys = None
        self.units = None
        self.norm_gt = None
        self.total_gt_number = 0
        self.row_count = 0
        self.gt_entries = []

        self.prepare_data()

    def prepare_data(self):
        self.tables = load_tables(self.tables_csv_path)
        self.ground_truth = load_tables(self.gt_path)
        self.keys, self.units = load_ontos(self.ontology_file, self.core_onto_file, True)
        self.tables, self.ground_truth = plix_evaluation.normalize_input(self.tables, self.ground_truth,
                                                                         self.keys)
        self.total_gt_number, self.row_count, self.gt_entries = prepare_gt(self.ground_truth)
        self.print_gt_statistics()

    @timer
    def get_plix_results(self):
        results = plix_evaluation.extract_kvu(self.tables, self.keys, self.units)
        formatted_results = plix_evaluation.format_results(results)
        return formatted_results

    @timer
    def get_plix_pivot_results(self):
        results = plix_evaluation.extract_kvu(self.tables, self.keys, self.units, pivot=True)
        formatted_results = plix_evaluation.format_results(results)
        return formatted_results

    @timer
    def get_spacy_simple_table_results(self):
        spacy_matcher = sst.SpacySimpleTableMatcher(self.keys, self.units, self.tables)
        results = spacy_matcher.do_extraction()
        return results

    @timer
    def get_spacy_simple_row_results(self):
        spacy_matcher = ssr.SpacySimpleRowMatcher(self.keys, self.units, self.tables)
        results = spacy_matcher.do_extraction()
        return results

    @timer
    def get_spacy_row_units_results(self):
        spacy_matcher = ssru.SpacySimpleRowUnitMatcher(self.keys, self.units, self.tables)
        results = spacy_matcher.do_extraction()
        return results

    @timer
    def get_spacy_table_units_results(self):
        spacy_matcher = sstu.SpacySimpleTableUnitMatcher(self.keys, self.units, self.tables)
        results = spacy_matcher.do_extraction()
        return results

    @timer
    def get_spacy_ex_table_results(self):
        spacy_matcher = SET.SpacyExtendedTableMatcher(self.keys, self.units, self.tables)
        results = spacy_matcher.do_extraction()
        return results

    @timer
    def get_spacy_ex_table_unit_results(self):
        spacy_matcher = setu.SpacyExtendedTableUnitMatcher(self.keys, self.units, self.tables)
        results = spacy_matcher.do_extraction()
        return results

    @timer
    def get_spacy_ex_row_results(self):
        spacy_matcher = ser.SpacyExtendedRowMatcher(self.keys, self.units, self.tables)
        results = spacy_matcher.do_extraction()
        return results

    @timer
    def get_spacy_ex_row_unit_results(self):
        spacy_matcher = seru.SpacyExtendedRowUnitMatcher(self.keys, self.units, self.tables)
        results = spacy_matcher.do_extraction()
        return results

    @timer
    def get_stanza_simple_unit_results(self):
        stanza_matcher = SSU.StanzaSimpleUnitMatcher(self.keys, self.units, self.tables)
        results = stanza_matcher.do_extraction()
        return results

    @timer
    def get_stanza_ex_unit_results(self):
        stanza_matcher = SEU.StanzaExtendedRowUnitMatcher(self.keys, self.units, self.tables)
        results = stanza_matcher.do_extraction()
        return results
    @timer
    def evaluate_kvu_extraction_tables(self):
        """
        run all evaluations defined in args.evaluations sequentially.
        """
        for eval_method in self.evaluation_methods:
            # extract kvu tuples
            extraction_results = self.eval_methods[eval_method]()

            print_extraction_stats(len(extraction_results), self.row_count)
            # calculation of evaluation metrics
            gt_matches, gt_match_count, gt_misses = find_misses(self.gt_entries, extraction_results)
            kvu_matches, kvu_match_count, kvu_misses = find_misses(extraction_results, self.gt_entries)
            self.save_misses(gt_misses, "in_gt_but_not_found", eval_method)
            self.save_misses(kvu_misses, "found_but_not_in_gt", eval_method)

            false_negatives, false_positives, true_positives, true_negatives = calculate_pos_and_neg(len(kvu_misses),
                                                                                                     len(gt_misses),
                                                                                                     len(extraction_results),
                                                                                                     kvu_match_count,
                                                                                                     self.row_count)
            results = calculate_metrics(true_positives, true_negatives, false_positives, false_negatives)
            self.save_results(results, eval_method, do_print=True)

    def validate_evaluation_methods(self, eval_methods):
        for mode in eval_methods:
            if mode not in self.eval_methods.keys():
                raise ValueError("Wrong evaluation method: " + mode)
        return eval_methods

    def print_gt_statistics(self):
        cf.log("the ground truth contains {} KVU tuples".format(self.total_gt_number))
        cf.log("GT: positives: {}, negatives: {}, total/# rows: {}".format(self.total_gt_number,
                                                                           self.row_count - self.total_gt_number,
                                                                           self.row_count))

    def save_results(self, results, method_name, do_print=False):
        """
        saves the calculated metrics to a file
        """
        results_file = os.path.join(self.arttab_path, "results_" + method_name + ".txt")
        result_str = ""
        for metric, value in results.items():
            result_str += "{}: {:.4f}\n".format(metric, value)
        if do_print:
            cf.log(result_str)
        with open(results_file, 'w+', encoding='utf-8') as f:
            f.write(result_str)

    def save_misses(self, misses, misses_name, method_name):
        """
        prints to all tuples that weren't found or were found extra to a file
        """
        misses_file = os.path.join(self.arttab_path, misses_name + "_" + method_name + ".txt")
        with open(misses_file, "w+") as f:
            for row in misses:
                f.write("{}\n".format(str(row)))
