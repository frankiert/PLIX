"""
This file provides methods for the KVU extraction.
"""
import pint

import plix.helpers.common_functions as cf

# for unit conversions
ureg = pint.UnitRegistry()


def is_value_unit_sane(value, unit, allowed_units):
    """
    Executes a last sanity check on the returned solution.

    :param str value: the value of a found solution, usually numeric
    :param str unit: the unit of the found solution, i.e km
    :param list allowed_units: allowed units to compare unit against.

    :return: bool describing the validity of the data
    :rtype: bool

    """
    value_empty = is_empty(value)
    no_required_units = not is_unit_required(allowed_units)
    unit_exists = not is_empty(unit)
    is_sane = not value_empty and (no_required_units or unit_exists)
    return is_sane


def is_unit_correct(unit, allowed_units):
    """
    checks whether a found unit is correct.

    :param str unit:
    :param list allowed_units:

    :return: true if unit is in allowed units or symbols
    :rtype: bool
    """
    return is_empty(unit) and not is_unit_required(allowed_units) or unit in allowed_units


def is_empty(text):
    """
    Checks if a text is empty.

    :return: true if the text is emtpy
    :rtype: bool
    """
    return text is None or text.strip() == ""


def is_unit_required(allowed_units):
    """
    Checks if a unit is required.

    :return: true if there are units or symbols
    :rtype: bool
    """
    return len(allowed_units) > 0


def build_units_dict(main_key, units):
    """
    This function builds a dictionary that holds all units and symbols that are allowed for the main_key and all units
    and symbols from the domain knowledge.

    :param str main_key: key for which the units should be compiled
    :param dict units: units dictionary

    :returns: dictionary of all units and all allowed units for the main_key
    :rtype: dict
    """
    all_units = __build_all_units_list(units)
    all_symbols = __build_all_symbols_list(units)
    allowed_units = units[main_key]['prefixed_units'] + units[main_key]['base_units']
    allowed_symbols = units[main_key]['prefixed_symbols'] + units[main_key]['base_symbols']
    # object to store all allowed units/symbols for the found key, as well as all units/symbols
    units_and_symbols = {
        'allowed_symbols': allowed_symbols,
        'all_symbols': all_symbols,
        'allowed_units': allowed_units,
        'all_units': all_units
    }
    return units_and_symbols


def transform_unit(kvu_list, units):
    """
    This is a function to convert measurement units of key-value-unit tuples if necessary.
    The conversion are done with the help of the library pint.

    In special cases, the value extracted is the radius, and the needed value is the diameter. Here, the diameter is
    calculated with d=2*r.

    :param list kvu_list: list with all filtered key-value pairs
    :param dict units: units from the domain knowledge

    :returns: kvu_list with converted entries
    :rtype: list
    """
    # kv_pair = [ 0 file_path, 1 key, 2 synonym key, 3 value, 4 unit, 5 cell 6 class list]
    for kv_pair in kvu_list:
        key = kv_pair[1]
        unit = kv_pair[4]
        value = kv_pair[3]
        if units[key]['base_symbols']:
            base_unit = units[key]['base_symbols'][0]
            if not unit == base_unit:
                cf.log('Unit transform needed: ' + str(kv_pair))
                try:
                    value = value.replace(" ", "")
                    unit = unit.replace(" ", "")
                    quantity = ureg.Quantity(float(value), unit)
                    kv_pair[3] = quantity.to(base_unit).magnitude
                    kv_pair[4] = base_unit
                except ValueError as er:
                    print("error converting: " + value)
        if needs_radius_conversion(key, kv_pair):  # radius -> diameter
            cf.log('Radius to diameter conversion needed: ' + str(kv_pair))
            kv_pair[3] = str(float(value) * 2)
    return kvu_list


def needs_radius_conversion(key, kv_pair):
    """
    checks where a value needs to be converted from diameter to radius.

    :param str key: the found key
    :param list kv_pair: the extraction entry

    :returns: true if conversion is needed
    :rtype: bool
    """
    return ('radius' in kv_pair[5] or 'radii' in kv_pair[5]) and 'diameter' in key.lower()


def __build_all_units_list(units_):
    units_set = set()
    for entry, entry_dict in units_.items():
        key_main_unit = entry_dict['base_units']
        key_units = entry_dict['prefixed_units']
        units_set.update(key_main_unit)
        units_set.update(key_units)
    return list(units_set)


def __build_all_symbols_list(symbols):
    symbols_set = set()
    for entry, entry_dict in symbols.items():
        key_main_symbol = entry_dict['base_symbols']
        key_symbols = entry_dict['prefixed_symbols']
        symbols_set.update(key_main_symbol)
        symbols_set.update(key_symbols)
    return list(symbols_set)
