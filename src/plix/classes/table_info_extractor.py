"""
This class is used for the key-value extraction (KVE) from tables.

The resulting files have the following format:

+-----------+------------------+-----+--------------------------------------+---------------------+------------------------------------------------------+--------------------------------+-------------------------------+
| index     | FileName         | Key | MatchedSynonym                       | Value               | Unit                                                 | Row                            | Classification                |
+===========+==================+=====+======================================+=====================+======================================================+================================+===============================+
| row index | Name of pdf file | Key | corresponding labels in the DK       | corresponding value | measurement unit of the value, '' if none was found  | row in which the key was found | list of classification labels |
+-----------+------------------+-----+--------------------------------------+---------------------+------------------------------------------------------+--------------------------------+-------------------------------+
"""
import pandas as pd
from nltk import edit_distance
from nltk import ngrams

import plix.helpers.common_functions as cf
import plix.helpers.extraction_utils as eu
import plix.helpers.kvu_utils as kvuu


def extract_table_kvu(df, labels, units, do_pivot_search, normalized_input=True, unit_check=True, use_synonyms=True,
                      lev_dist=1):
    """
    This function holds the main functionality of the table key-value-unit extraction (KVUE).

    Here, the information from the tables from `df` is extracted based on the passed `labels` list.
    It is considered as the keys (list of lists, one list equals all synonyms of the key).
    In addition, measurement units are extracted. They need to be defined in a domain knowledge and passed as `units`.

    **Please note:** *df* needs to be in the format defined in the data extraction!

    :param pd.DataFrame df: dataframe object with the data extraction results
    :param list labels: keys and synonyms (of the domain knowledge)
    :param dict units: measurement names and units (from the domain knowledge)
    :param bool do_pivot_search: toggle to enable pivot value-unit search in the tables, set to False by default
    :param bool normalized_input: toggle to use normalized input, set to True by default
    :param bool unit_check: toggle to enable unit sanity checks, set to True by default
    :param bool use_synonyms: toggle to search for synonyms and not just the main key, set to True by default
    :param int lev_dist: sets the Levenshtein distance for the found keys, set to 1 by default

    :returns: all KVU tuples found in the tables
    :rtype: list
    """

    # use normalized tables if present, else take normal table data
    tables = df['NormalizedTableData'] if normalized_input and cf.df_has_column(df, 'NormalizedTableData') \
        else df['TableData']
    files = df['Filename']
    classes = df['Classification'] if 'Classification' in df.columns else [' '] * len(files)
    kvu_results = __find_tuples(tables, files, classes, labels, units, do_pivot_search, unit_check, use_synonyms,
                                lev_dist)
    return kvu_results


def remove_text_table_duplicates(df_tab, df_text):
    """
    This func merges the KVU tuples from the text and table extraction. After concatenating both dataframes,
    it removes the duplicates. Therefore, for rows that have the same 'FileName', 'Key', 'MatchedSynonym', 'Value',
    'Unit' cells, one of both rows is removed. Finally, the resulting merged dataframe is sorted by 'FileName'.

    :param pd.DataFrame df_tab: dataframe object with the KVU tuples of the table extraction
    :param pd.DataFrame df_text: dataframe object with the KVU tuples of the table extraction

    :returns: merged dataframe object
    :rtype: pd.DataFrame
    """
    return (pd.concat([df_tab, df_text]).drop_duplicates(subset=['FileName', 'Key', 'MatchedSynonym', 'Value', 'Unit'])
            .sort_values(by='FileName').reset_index(drop=True))


def __find_tuples(tables, files, classes, labels, units, do_pivot_search, unit_check, use_synonyms, lev_dist):
    results = []
    count = 0
    for (tables, file, class_list) in zip(tables, files, classes):
        for t_num, table in enumerate(tables):
            for i, key in enumerate(labels):
                for j, row in enumerate(table):
                    possible_kvu_tuple = __match_key_value_unit(table, row, key, units, file, t_num, class_list, j,
                                                                do_pivot_search, unit_check, use_synonyms, lev_dist)
                    if possible_kvu_tuple:
                        results.append(possible_kvu_tuple)
                        count += 1
                        continue
    cf.log("Found " + str(count) + " key-value-unit tuples")
    return results


def __extract_ngrams(cell, synonym):
    n = len(synonym.split(" "))
    return list(ngrams(cell.split(" "), n))


def __match_key_value_unit(table, row, key, units, file, t_num, classes, j, do_pivot_search, unit_check, use_synonyms,
                           lev_dist):
    main_key = key[0]  # keyword is first in keyword list
    units_and_symbols = kvuu.build_units_dict(main_key, units)
    for k, cell in enumerate(row):
        synonym_list = key[1:] if use_synonyms else [main_key]
        for synonym in synonym_list:
            n_grams = __extract_ngrams(cell, synonym)
            for gram in n_grams:
                gram = " ".join(word for word in gram)
                if edit_distance(gram, synonym) <= lev_dist:
                    # if synonym in cell:
                    value, unit = __find_value_unit(table, j, k, units_and_symbols, do_pivot_search, unit_check)
                    if kvuu.is_value_unit_sane(value, unit, (units_and_symbols['allowed_symbols'] +
                                                             units_and_symbols['allowed_units'])):
                        # no further iteration needed - return
                        return [file, main_key, synonym, value, unit, row, str(t_num), classes]
    return []  # nothing found - return


def __yield_new_possible_solution(table, j, k, pattern):
    """
    Creates a new string representation of possible solution by
    concatenating cells by a given pattern, which can subsequently be parsed for key, value, unit.
    The solution is derived from cell coordinates, respective to the key, 
    i.e. [(0,0),(0,1),(0,2)], where the origin (0,0) is the position of the found key or respective synonym. 
    For the given example [(0,0),(0,1),(0,2)], that would mean take the key (0,0)
    and the adjacent 2 cells in line (0,1) and (0,2).

    i.e.
     ______________ 
    |__|__|__|__|__|
    |__|o_|x_|x_|__|
    |__|__|__|__|__|
    |__|__|__|__|__|
    |__|__|__|__|__|


    To ensure, the solution is valid, the coordinates are cut off if they're extending the table's boundaries.

    :param list table: tables to search in
    :param list pattern: pattern list of type [(0,0),(0,1),(0,2)], describing the respective distance from the found key
    :param int j: row coordinate
    :param int k: column coordinate

    :returns: string with new possible concatenated solution
    :rtype: str
    """
    target = []
    table_height = len(table)

    for dj, dk in pattern:  # dj -> y-distance from origin, dk-> x-distance from origin
        # Make sure we don't exceed y dimension
        jj = min(max(j + dj, 0), table_height - 1)

        # Make sure we don't exceed x dimension
        column_with = len(table[jj]) - 1
        kk = min(max(k + dk, 0), column_with)

        # retrieve cell
        cell = table[jj][kk]
        if cell not in target:
            target.append(cell)

    return " ".join(target)


def __find_value_unit(table, j, k, units_and_symbols, do_pivot_search, unit_check):
    """
    tries to retrieve a value unit tuple given a position in the respective table,
    where a key-hit had been created.


    First look into the cell itself if everything is given:
     _____ j
    |__|__|
    |__|__|
    k

    "OntoKey Value Unit"
    "OntoKey Unit Value"


    I.  Row - Value Unit in Adjacent Cells
     ______________     ______________ 
    |__|__|__|__|__|   |__|__|__|__|__|   
    |__|o_|x_|x_|__|   |__|o_|__|x_|x_|   
    |__|__|__|__|__|   |__|__|__|__|__|   ...   
    |__|__|__|__|__|   |__|__|__|__|__|   
    |__|__|__|__|__|   |__|__|__|__|__|   
   
    II. Exhaustive Row Search
     ______________     ______________     ______________ 
    |__|__|__|__|__|   |__|__|__|__|__|   |__|__|__|__|__|
    |__|o_|x_|__|__|   |__|o_|x_|x_|__|   |__|o_|x_|x_|x_|
    |__|__|__|__|__|   |__|__|__|__|__|   |__|__|__|__|__|
    |__|__|__|__|__|   |__|__|__|__|__|   |__|__|__|__|__|
    |__|__|__|__|__|   |__|__|__|__|__|   |__|__|__|__|__|

    II.  Exhaustive Column Search
     ______________     ______________     ______________  
    |__|__|__|__|__|   |__|__|__|__|__|   |__|__|__|__|__| 
    |__|o_|__|__|__|   |__|o_|__|__|__|   |__|o_|__|__|__| 
    |__|x_|__|__|__|   |__|x_|__|__|__|   |__|x_|__|__|__| 
    |__|__|__|__|__|   |__|x_|__|__|__|   |__|x_|__|__|__| 
    |__|__|__|__|__|   |__|__|__|__|__|   |__|x_|__|__|__|  

    III. Pivot Tables (European Pattern)
     ______________     ______________ 
    |__|__|x_|__|__|   |__|__|o_|__|__|
    |__|__|__|__|__|   |__|__|__|__|__|
    |o_|__|x_|__|__|   |x_|__|x_|__|__|
    |__|__|__|__|__|   |__|__|__|__|__|
    |__|__|__|__|__|   |__|__|__|__|__|    

    

    # i.e.

    Table off (i.e. bc. of collapsed cells) (not used)
     ______________     ______________ 
    |__|__|__|__|__|   |__|__|__|__|__|
    |__|o_|  |  |__|   |__|o_|  |x_|__|
    |__|__|x_|x_|__|   |__|__|x_|  |__|
    |__|__|__|__|__|   |__|__|__|__|__|
    |__|__|__|__|__|   |__|__|__|__|__|

     ______________     ______________ 
    |__|__|__|__|__|   |__|__|__|__|__|
    |__|o_|__|__|__|   |__|o____|__|__|
    |__|___x_|__|__|   |__|__|x_|__|__| (i.e. subdivided columns)
    |__|x____|__|__|   |__|__|x_|__|__|
    |__|__|__|__|__|   |__|__|x_|__|__|


    :returns: value unit tuple if found - otherwise empty strings tuple ("", "")
    :rtype: tuple
    """
    # initialize search patterns for cell concatenation creates a probable solution
    # containing key value unit within one string (not necessarily in that order)
    row_length, table_height = len(table[j]), len(table)

    left_row_length = row_length - k
    left_table_height = table_height - j

    value_unit_adjacent_cell = [[(0, 0), (0, k_), (0, k_ + 1)] for k_ in range(1, left_row_length - 1)]
    exhaustive_row_search = [[*((0, kk_) for kk_ in range(k_))] for k_ in range(2, left_row_length + 1)]

    search_patterns = [[(0, 0)]] + value_unit_adjacent_cell + exhaustive_row_search

    # Pivot Search Pattern Horizontal
    if do_pivot_search:
        exhaustive_column_search = [[*((kk_, 0) for kk_ in range(k_))] for k_ in range(2, left_table_height + 1)]
        search_patterns += exhaustive_column_search
        is_possible_pivot_entry = (1 < row_length == len(table[0]) and k == 0)
        if is_possible_pivot_entry:
            pivot_entries = [[(0, 0), (-j, k_), (0, k_)] for k_ in range(1, left_row_length)]
            search_patterns += pivot_entries

    # initialize something, just in case
    unit, value = "", ""

    # examine the patterns and return, as soon as a valid combination was found
    for pattern_id, pattern in enumerate(search_patterns):
        possible_kvu_string = __yield_new_possible_solution(table, j, k, pattern)
        temp_value, temp_unit, is_valid_solution = eu.find_value_and_unit(possible_kvu_string, units_and_symbols,
                                                                          unit_check)
        if is_valid_solution:
            value, unit = temp_value, temp_unit
            break
    return value, unit
