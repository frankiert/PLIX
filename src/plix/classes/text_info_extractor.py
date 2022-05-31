"""
This module contains functions that handle the extraction of text, especially a key-value-unit triplet,
from a dataframe.
"""

import re

from nltk import sent_tokenize

import plix.helpers.common_functions as cf
import plix.helpers.extraction_utils as eu
import plix.helpers.kvu_utils as kvuu


def extract_text_kvu(df, keywords, units, max_len_text):
    """
    Function to extract key-value-unit from text in all pdf data sheets based on classes in the DK file.

    :param list keywords: list of synonyms per keyword
    :param dict units: content of the unit domain knowledge
    :param DataFrame df: the dataframe object with the extracted data
    :param str max_len_text: max length of the sentence context

    :returns: list of all key/value/unit with file_path
    :rtype: list
    """
    # use normalized text if present, else take normal table data
    texts = df['NormalizedText'] if cf.df_has_column(df, 'NormalizedText') else df['MeaningfulText']
    files = df['Filename']
    classes = df['Classification'] if 'Classification' in df.columns else [' '] * len(files)
    kvu_results = __find_tuples(texts, files, classes, keywords, units, max_len_text)
    return kvu_results


def __find_tuples(text_pages, files, classes, keywords, units, max_len_text):
    results = []
    count = 0
    for (pages, file, class_list) in zip(text_pages, files, classes):
        for page_no, page_text in pages.items():
            for i, key in enumerate(keywords):
                key_kvu_tuples = __extract_key_value_unit(key, page_text, units, file, page_no, class_list,
                                                          max_len_text)
                if key_kvu_tuples:
                    results = results + key_kvu_tuples
                    count += len(key_kvu_tuples)
    cf.log("Found " + str(count) + " key-value-unit tuples")
    return results


def __all_values_sane(tuples, allowed_values):
    return all([kvuu.is_value_unit_sane(tuple_[0], tuple_[1], allowed_values) for tuple_ in tuples])


def __extract_key_value_unit(current_keys, text, units, file, page_num, classes, max_len_text):
    result_tuples = []
    main_key = current_keys[0]
    units_and_symbols = kvuu.build_units_dict(main_key, units)
    for synonym in current_keys[1:]:
        if synonym in text:
            possible_tuples, surrounding_text = __find_all_value_unit_per_synonym(text, synonym, units_and_symbols,
                                                                                  max_len_text)
            if possible_tuples:
                for tuple_ in possible_tuples:
                    if kvuu.is_value_unit_sane(tuple_[0], tuple_[1], units_and_symbols['allowed_symbols'] +
                                                                     units_and_symbols['allowed_units']):
                        result_tuples.append([file, main_key, synonym, tuple_[0], tuple_[1], surrounding_text,
                                              str(page_num), classes])
                return result_tuples
    return []


def __find_all_value_unit_per_synonym(text, synonym, units_symbols, max_len_text):
    value_unit = []
    matches = re.finditer(synonym, text)
    possible_vu_string = ""
    if matches:
        for match in matches:
            match_start_pos = match.start()
            right_text, left_text = __get_left_and_right_text_window(text, synonym, match_start_pos, max_len_text)
            possible_vu_string = "{}; {}".format(right_text, left_text)
            value, unit, is_valid = eu.find_value_and_unit(possible_vu_string, units_symbols, unit_check=True)
            if is_valid:
                value_unit.append([value, unit])
    return value_unit, possible_vu_string


def __get_left_and_right_text_window(text, key, match_start_pos, max_len_text):
    text_len = len(text)
    shorten_left_bound = match_start_pos - max_len_text if (match_start_pos - max_len_text) > 0 else 0
    shorten_right_bound = match_start_pos + max_len_text if (match_start_pos + max_len_text) < text_len \
        else text_len - 1
    shortened_text = text[shorten_left_bound:shorten_right_bound]
    sentences = sent_tokenize(shortened_text)
    ind = __get_key_sentence_index(key, sentences)
    sentence = sentences[ind]
    split_sentence = re.split(key, sentence, maxsplit=1)
    if len(split_sentence) > 1:
        right = split_sentence[1]
        left = split_sentence[0]
    else:
        right = ""
        left = split_sentence[0]
    return right, left


def __get_key_sentence_index(key, sentences):
    for i, sent in enumerate(sentences):
        if key in sent:
            return i
    return 0
