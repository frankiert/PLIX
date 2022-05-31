"""
This file provides methods to help with the extraction.
"""
import re

import plix.helpers.kvu_utils as kvuu
import plix.nlp_assets as nlp_assets

VALUE_REGEX = re.compile(nlp_assets.REGEX_3D_VALUE)


def find_value_and_unit(possible_kvu_string, units_and_symbols, unit_check):
    """
    Processes data to retrieve key, value and unit tuples from a given cell space.

    :param str possible_kvu_string: string containing possible key, value, unit combination within a single string
    :param dict units_and_symbols: data structure for units and symbols
    :param bool unit_check: toggle if unit check should be performed

    :returns: value, unit, is_valid_solution if found
    :rtype: tuple
    """
    is_unit_required = kvuu.is_unit_required(units_and_symbols['allowed_units'] + units_and_symbols['allowed_symbols'])
    is_valid_solution = False
    # we can assume there has to be a [key - value - unit tuple] within that space already
    # find unit first, before accepting any value!
    unit, unit_list = __find_unit(possible_kvu_string, all_units=(units_and_symbols['all_symbols'] +
                                                                  units_and_symbols['all_units']))
    if unit_check:
        is_unit_correct = kvuu.is_unit_correct(unit, units_and_symbols['allowed_symbols'] +
                                               units_and_symbols['allowed_units'])
    else:
        is_unit_correct = ((unit is None or unit == "") and not is_unit_required) or (unit is not None or unit != "")

    # needs a unit, but wrong one was found -> return
    if unit is not None and is_unit_required and not is_unit_correct:
        return None, None, is_valid_solution
    # does NOT need a unit, but one was found (e.g. [Number of coils, 12, cm]) -> return
    elif unit is not None and not is_unit_required:
        return None, None, is_valid_solution

    # otherwise, keep looking
    if unit is None:
        unit = ""
    value = __extract_value(possible_kvu_string, unit_list)
    if value is None or value == "":
        return None, None, is_valid_solution
    else:
        # If we managed until here, the solution is accepted
        is_valid_solution = True

    return value, unit, is_valid_solution


def __find_closest_completest_unit(match_list):
    # if more than 1 matched unit
    if len(match_list) > 1:
        # check if matches overlap by checking for intersection of start positions
        start_positions = [x[0].start() for x in match_list]
        intersection_start = set([x for x in start_positions if start_positions.count(x) > 1])
        if intersection_start:
            # take the one closest to keyword aka the min of the positions
            inter_start = min(intersection_start)
            # get all overlapping matches for the start position
            overlapping_matches = [m for m in match_list if m[0].start() == inter_start]
            # longest unit
            match_ = max(overlapping_matches, key=lambda x: len(x[1]))[1]
        else:
            # no overlaps, take unit closest to key
            match_ = min(match_list, key=lambda x: x[0].start())[1]
    else:
        # just one, return this
        match_ = match_list[0][1]
    return match_


def __find_all_units(search_string, units):
    result_list = []
    for expression in set(units):
        result = re.search(fr"(?:^|[\b\s\d])({re.escape(expression)})(?:[\b\s\d]|$)", search_string)
        if result:
            result_list.append([result, expression])
    return result_list


def __find_unit(search_string, all_units):
    result_list = __find_all_units(search_string, all_units)
    if len(result_list) > 0:
        return __find_closest_completest_unit(result_list), result_list
    else:
        return None, result_list


def __extract_value(cell, units_in_cell):
    if units_in_cell:
        # sort by length to avoid missing symbols from compound units (deg / sec)
        units_in_cell.sort(key=lambda x: len(x[1]), reverse=True)
        for m_ in units_in_cell:
            # remove all units from cell
            cell = cell.replace(m_[1], "")
    # find FIRST value (aka closest to key)
    value = VALUE_REGEX.search(cell)
    if value:
        value = value.group(0).strip()
    return value
