"""
This module contains functions to process dataframe containing text
extracted from data sheets.
"""
import json
import re
from string import printable

import ftfy

import plix.nlp_assets as nlp_assets


def replace_camelcase_with_space(text):
    """
    Replaces camel cases with spaces in a text.
    :param str text:

    :returns: edited text
    :rtype: str
    """
    text = re.sub(nlp_assets.REGEX['camel_case'], nlp_assets.REGEX['replace_space'], text)
    text = re.sub(nlp_assets.REGEX['camel_case2'], nlp_assets.REGEX['replace_space'], text)
    return text


def load_text(text):
    """
    Loads text as json, if it's not a json text, it is returned plain.
    :param Any text: text to load

    :returns: loaded text
    :rtype: dict or list
    """
    if type(text) in [dict, list]:
        return text
    else:
        return json.loads(text)


def replace_with_space(regex, text_json):
    """
    Replaces a regex expression with spaces in a text.

    :param str regex: expression to replace
    :param Any text_json: the text

    :returns: edited text
    :rtype: dict or list
    """
    json_obj = load_text(text_json)
    for i in json_obj:
        json_obj[i] = re.sub(regex, nlp_assets.SPACE, json_obj[i])
    return json_obj


def replace_without_space(regex, text_json):
    """
    Replaces a regex expression with ''.

    :param str regex: expression to replace
    :param Any text_json: the text

    :returns: edited text
    :rtype: dict or list
    """
    json_obj = load_text(text_json)
    for i in json_obj:
        json_obj[i] = re.sub(regex, '', json_obj[i])
    return json_obj


def remove_non_printable(text_json):
    """
    Removes all nonprintable charaters with spaces in a text.

    :param Any text_json: the text

    :returns: edited text
    :rtype: dict or list
    """
    json_obj = load_text(text_json)
    for i in json_obj:
        json_obj[i] = ''.join(filter(lambda x: x in printable, ftfy.fix_text(json_obj[i])))
    return json_obj


def cut_end_of_text(text_json):
    """
    Cuts the end of a text if one of the nlp_assets.TEXT_CUT_KEYWORDS is found.

    :param Any text_json: the text

    :returns: edited text
    :rtype: dict or list
    """
    # cuts the text if one word from nlp_assets.TEXT_CUT_KEYWORDS is found
    # useful for papers to remove literature sections
    json_obj = load_text(text_json)
    do_cut = False
    for i in json_obj:
        if do_cut:
            json_obj[i] = ''
        elif isinstance(json_obj[i], str):
            for word in nlp_assets.TEXT_CUT_KEYWORDS:
                found_word = re.search(r'\b({})\b'.format(word), json_obj[i])
                if found_word:
                    json_obj[i] = json_obj[i][:found_word.start()]
                    do_cut = True
    return json_obj
