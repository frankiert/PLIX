"""
Methods to run seperate parts of run PLIX' pipeline for the evaluation.
"""
import plix.classes.normalizer as nm
import plix.classes.table_info_extractor as taie


def normalize_input(tables, gt, key_onto):
    gt['NormalizedTableData'] = gt['TableData'].apply(lambda x: nm.normalize_tables(x, key_onto, True))
    tables['NormalizedTableData'] = tables['TableData'].apply(lambda x: nm.normalize_tables(x, key_onto, True))
    return tables, gt


def extract_kvu(tables, keys, units, pivot=False, normalized_input=True, unit_check=True, use_synonyms=True,
                lev_dist=1):
    return taie.extract_table_kvu(tables, keys, units, pivot, normalized_input, unit_check, use_synonyms, lev_dist)


def format_results(results):
    # [file, main_key, synonym, value, unit, row, str(t_num), classes]
    results = [[entry[0], entry[1].lower(), entry[3], entry[4]] for entry in results]
    return results
