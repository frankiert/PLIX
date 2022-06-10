"""
This file holds functionality to normalize data structures used in PLIX. They are:

- domain knowledge (list of lists for keywords, dictionary with symbols and units for units)
- plain text strings
- tables (list of lists)
- dictionaries of text with page numbers as keys

Each normalization method

- replaces known extraction errors and symbols
- tokenizes the string and transforms it back into a string
- transforms the string to lower case
- corrects common spelling errors with pyspellchecker (currenly disabled)
"""
import itertools
import re
from copy import deepcopy

import text_unidecode
from pandas import Series

import plix.classes.tokenizer as tk
import plix.nlp_assets as nlp_assets


####################################################################################################################
# NORMALIZATION STEPS                                                                                              #
####################################################################################################################


def normalize_tables_from_pd_series(series, keywords, do_table_multiple_normalization):
    """
    Method for the pipeline. Runs the tables normalization for a pandas Series object.

    :param pd.Series series: column with the tables to normalize from the extraction results
    :param list keywords: keywords from the domain knowledge
    :param bool do_table_multiple_normalization: toggle for normalization of multiple keys in one cell

    :returns: the normalized tables
    :rtype: pd.Series
    """
    norm_results = []
    for cell in series:
        norm_tables = normalize_tables(cell, keywords, do_table_multiple_normalization)
        norm_results.append(norm_tables)
    return Series(norm_results)


def normalize_text_from_pd_series(series):
    """
    Method for the pipeline. Runs the text normalization for a pandas Series object.

    :param pd.Series series: column with the text to normalize from the extraction results

    :returns: the normalized tables
    :rtype: list
    """
    norm_results = []
    for cell in series:
        norm_text = normalize_text_per_page(cell)
        norm_results.append(norm_text)
    return Series(norm_results)


def normalize_text(text):
    """
    Normalizes a string of text. The steps are described above.

    :param str text: text to be normalized

    :returns: normalized text
    :rtype: str
    """
    # return correct_spelling(to_lower_case(tokenize(replace_symbols(text))), tokenizer)
    return __to_lower_case(__tokenize(__replace_symbols(text)))


def normalize_tables(tables, keywords, requires_multiple_normalization):
    """
    Performs the normalization steps on tables (as a list of lists). if `config.DO_TABLE_MULTIPLE_NORMALIZATION`
    is enabled, table rows with multiple keywords in a cell get split.

    :param list tables: tables to be normalized
    :param list keywords: list of keywords from the domain knowledge
    :param bool requires_multiple_normalization: flag if table normalization should perform  row splitting for multiple
    keywords in a cell

    :returns: normalized tables as a list of lists
    :rtype: list
    """
    normalized_tables = []
    keyword_set = set(itertools.chain.from_iterable(keywords))
    for table in tables:
        norm_table = __normalize_table(table)
        # multiple entities per cells normalization into separate rows
        if requires_multiple_normalization:
            norm_table = __normalize_multiple_keys_per_row(norm_table, keyword_set)
        normalized_tables.append(norm_table)
    return normalized_tables


def normalize_keyword_dk(key_dk):
    """
    Normalizes the keywords and synonyms from the domain knowledge.

    :param list key_dk: list of keywords from the domain knowledge

    :returns: normalized list of keywords of the domain knowledge
    :rtype: list
    """
    normalized_keywords = []
    for synonym_list in key_dk:
        normalized_keywords.append(list(dict.fromkeys(normalize_text(k) for k in synonym_list).keys()))
    return normalized_keywords


def normalize_unit_dk(unit_dk):
    """
    Normalizes the units and symbols of the unit domain knowledge.

    :param dict unit_dk: dictionary with units from the domain knowledge

    :returns: normalized units and symbols
    :rtype: dict
    """
    unit_dict_items = ['base_units', 'prefixed_units', 'base_symbols', 'prefixed_symbols']
    normalized_units = {}
    for entry, entry_dict in unit_dk.items():
        norm_entry = normalize_text(entry)
        norm_entry_dict = {}
        i = 0
        for unit_symbol, unit_symbol_list in entry_dict.items():
            norm_unit_list = []
            for unit in unit_symbol_list:
                norm_unit_list.append(normalize_text(unit))
            norm_entry_dict[unit_dict_items[i]] = norm_unit_list
            i += 1
        normalized_units[norm_entry] = norm_entry_dict
    return normalized_units


def normalize_text_per_page(text_dict):
    """
    Normalizes pages of text in a dictionary. The key has to be the page number.

    :param dict text_dict: text per page

    :returns: normalized dictionary of pages of text
    :rtype: dict
    """
    normalized_text = {}
    for page_no, page_text in text_dict.items():
        if isinstance(page_no, int):
            normalized_text[page_no] = normalize_text(str(page_text))
        if isinstance(page_text, int):
            normalized_text[page_no] = page_text
    return normalized_text


def __tokenize(text):
    return ' '.join(word for word in tk.tokenize(text))


def __replace_symbols(text):
    # replaces symbols defined in two dictionaries in nlp_assets
    for old, new in nlp_assets.REPLACE_PATTERNS.items():
        if old in text:
            text = text.replace(old, new)
    text = text_unidecode.unidecode(text)
    return text


def __to_lower_case(text):
    return text.lower()


def __normalize_table(table):
    norm_table = []
    for row in table:
        norm_row = [normalize_text(cell) for cell in row]
        norm_table.append(norm_row)
    return norm_table


####################################################################################################################
# TABLE NORMALIZATION HELPERS                                                                                      #
####################################################################################################################
def __find_multiple_values(row, matched_index):
    value_left = ''
    value_right = ''
    values_index = 0
    # only look right from keywords to find value
    for i, cell in enumerate(row[matched_index:]):
        # cell is number / number
        if re.match(nlp_assets.REGEX_whole_dimension_multiple, cell):
            values = cell.split(nlp_assets.ROW_MULTIPLE_KEYS_DELIMITER, 1)
            value_left = values[0].strip()
            value_right = values[1].strip()
            values_index = i
            # find unit
            unit_left = re.search(nlp_assets.REGEX['regex_unit'], value_left)
            unit_right = re.search(nlp_assets.REGEX['regex_unit'], value_right)
            if unit_left and not unit_right:
                value_right = value_right + " " + unit_left.group(0)
            if unit_right and not unit_left:
                value_left = value_left + " " + unit_right.group(0)
            break
        # cell is just one number (with unit)
        elif re.match(r"^" + nlp_assets.REGEX_whole_dimension + r"$", cell):
            value_left = cell
            value_right = cell
            values_index = i
            break
    return value_left, value_right, values_index


def __combine_new_keyword(left, right, keys_set):
    left_vec = left.split()
    right = re.split(r'[,\[(]', right)[0].strip()
    # take iteratively more parts from the whole keyword and combine with the other to form a new keyword
    # e.g. number of slots / poles -> number poles -> no match -> number of poles -> match
    for i in range(1, len(left_vec)):
        temp = ' '.join(left_vec[j] for j in range(i)) + ' ' + right
        if temp in keys_set:
            return temp
    return ''


def __contains_keyword(wordset: set, wordlist: list):
    return any([word in wordset for word in wordlist])


def __find_possible_keys(matched_cell, matched_side, keys_set):
    new_keys = matched_cell.split(nlp_assets.ROW_MULTIPLE_KEYS_DELIMITER, 1)
    # two independent keys, just split
    if matched_side == 'both':
        key_left = new_keys[0].strip()
        key_right = new_keys[1].strip()
    # left side is complete, try to combine key on right side
    elif matched_side == 'left':
        key_left = new_keys[0].strip()
        key_right = __combine_new_keyword(key_left, new_keys[1].strip(), keys_set)
    # right side is complete, try to combine key on left side
    elif matched_side == 'right':
        key_right = new_keys[1].strip()
        key_left = __combine_new_keyword(key_right, new_keys[0].strip(), keys_set)
    else:
        raise ValueError("Matched side can only be left, right, or both")
    return key_left, key_right


def __append_found_unit(key_left, key_right, unit):
    if len(unit) > 1:
        key_left = key_left + " " + unit[0]
        key_right = key_right + " " + unit[1]
    if len(unit) == 1:
        key_left = key_left + " " + unit[0]
        key_right = key_right + " " + unit[0]
    return key_left, key_right


def __find_multiple_keys(matched_cell, matched_side, keys_set):
    key_left, key_right = __find_possible_keys(matched_cell, matched_side, keys_set)
    # if one side of the 'key/ key' was followed by a unit, append it to the second part
    if key_left and key_right:
        unit = re.findall(nlp_assets.REGEX['regex_unit'], matched_cell)
        if unit:
            key_left, key_right = __append_found_unit(key_left, key_right, unit)
    return key_left, key_right


def __find_new_keys_and_values(row, match_index, keywords_set: set):
    # split only once, if more than one divider it will be separated in the next iteration of the loop
    multiple_entities = row[match_index].split(nlp_assets.ROW_MULTIPLE_KEYS_DELIMITER, 1)
    match_left = __contains_keyword(keywords_set, multiple_entities[0])
    match_right = __contains_keyword(keywords_set, multiple_entities[1])
    new_value_left = ''
    new_value_right = ''
    new_key_left = ''
    new_key_right = ''
    value_match_index = 0
    # based on found keywords, find separate keys and values to split
    if match_left and match_right:
        new_key_left, new_key_right = __find_multiple_keys(row[match_index], 'both', keywords_set)
        new_value_left, new_value_right, value_match_index = __find_multiple_values(row, match_index)
    elif match_left:
        new_key_left, new_key_right = __find_multiple_keys(row[match_index], 'left', keywords_set)
        new_value_left, new_value_right, value_match_index = __find_multiple_values(row, match_index)
    elif match_right:
        new_key_left, new_key_right = __find_multiple_keys(row[match_index], 'right', keywords_set)
        new_value_left, new_value_right, value_match_index = __find_multiple_values(row, match_index)
    return new_key_left, new_key_right, new_value_left, new_value_right, value_match_index


def __build_new_normalized_rows(row, new_key_left, new_key_right, new_value_left, new_value_right, match_index,
                                value_match_index):
    # build two rows from matched one
    new_row_top = deepcopy(row)  # left keyword and value
    new_row_bottom = deepcopy(row)  # right keyword and value
    new_row_top[match_index] = new_key_left
    new_row_top[value_match_index] = new_value_left
    new_row_bottom[match_index] = new_key_right
    new_row_bottom[value_match_index] = new_value_right
    return new_row_top, new_row_bottom


def __normalize_multiple_keys_per_row(table, keywords_set: set):
    # takes a table and searches for possible multiple keywords in one cell.
    for i, row in enumerate(table):
        match = [True if re.match(nlp_assets.REGEX['possible_multiple_entities'], cell) else False for cell in row]
        if not any(match):
            continue
        # If at least one is found, separate the two sides of / into two separate rows in the table
        match_index = match.index(True)
        if __contains_keyword(keywords_set, row[match_index]):

            new_key_left, new_key_right, new_value_left, new_value_right, value_match_index = \
                __find_new_keys_and_values(row, match_index, keywords_set)
            if not (new_value_left and new_value_right) or not (new_key_left and new_key_right):
                # nothing found
                continue
            new_row_top, new_row_bottom = __build_new_normalized_rows(row, new_key_left, new_key_right, new_value_left,
                                                                      new_value_right, match_index, value_match_index)
            # replace row with left key value into / cell
            table[i] = new_row_top
            # insert right key value below / cell
            table.insert(i + 1, new_row_bottom)
    return table
