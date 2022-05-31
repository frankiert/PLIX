"""
Methods to handle ontologies.
"""
import re
from collections import OrderedDict
from itertools import chain

import validators
from rdflib import Graph, URIRef, Literal, RDF
from rdflib.namespace import OWL

import evaluation.helpers.ontology_properties as OP
from plix import nlp_assets
from plix.classes import normalizer as NM
from plix.helpers import common_functions as CF
from plix.helpers import text_utils as TU


def is_keyword(keyword_onto, text):
    """
    Method to check if a string is a keyword.

    :param list keyword_onto: keyword data structure
    :param str text: the text to check

    :returns: true if text is a keyword from the ontology
    :rtype: bool
    """
    return text in list(set(list(chain.from_iterable(keyword_onto))))


def contains_keyword(keyword_onto, text):
    """
    simple method to check if the text contains a keyword from the ontology

    :param list keyword_onto: keyword data structure
    :param str text: the text to check

    :returns: True if a keyword from the ontology is present in the text
    :rtype: bool
    """
    return True if any([key in text for key in list(set(list(chain.from_iterable(keyword_onto))))]) else False


def build_units_dict(main_key, units):
    """
    build a dictionary that holds all units and symbols that are allowed for the main_key and all units and symbols from
    the domain knowledge.

    :param str main_key: key for which the units should be compiled
    :param dict units: units dictionary

    :returns: dictionary of all units and all allowed units for the main_key
    :rtype: dict
    """
    all_units = __build_all_units_list(units)
    all_symbols = __build_all_symbols_list(units)
    allowed_units = units[main_key]['prefixed_units']
    allowed_symbols = units[main_key]['prefixed_symbols']
    # object to store all allowed units/symbols for the found key, as well as all units/symbols
    units_and_symbols = {
        'allowed_symbols': allowed_symbols,
        'all_symbols': all_symbols,
        'allowed_units': allowed_units,
        'all_units': all_units
    }
    return units_and_symbols


def unit_ontology_update(new_unit_dict, new_labels_arr, input_files, output_file):
    """
    Overwrite unit ontology file with unit dict and labels

    :param dict new_unit_dict: a dictionary contain new units for each class
    :param [string] new_labels_arr: an array of labels for each class
    :param [string] input_files: a list of paths to the original ontology files
    :param string output_file: a path to an overwritten unit ontology file
    """
    # read original unit.ttl file
    graph = __create_rdf_graph(input_files)
    classes = __get_local_classes(graph, input_files)

    new_labels_dict = {}
    for labels in new_labels_arr:
        new_labels_dict[labels[0]] = labels[1:]

    for class_uri in classes:
        class_name = NM.normalize_text(__get_entity_name(class_uri))
        base_units = []
        prefixed_units = []
        base_symbols = []
        symbols = []
        if new_unit_dict[class_name]:
            base_units = new_unit_dict[class_name]['base_units']
            prefixed_units = new_unit_dict[class_name]['prefixed_units']
            base_symbols = new_unit_dict[class_name]['base_symbols']
            symbols = new_unit_dict[class_name]['prefixed_symbols']

        info_dict = {OP.WIKIDATA_ONT['labels']: [class_name],
                     OP.WIKIDATA_ONT['alt_label']: new_labels_dict[class_name],
                     OP.OM_ONT['base_unit']: base_units,
                     OP.OM_ONT['prefixed_unit']: prefixed_units,
                     OP.OM_ONT['base_symbol']: base_symbols,
                     OP.OM_ONT['symbol']: symbols}

        for key, values in info_dict.items():
            graph.remove((URIRef(class_uri),
                          URIRef(key), None))
            for value in values:
                graph.add((URIRef(class_uri),
                           URIRef(key),
                           Literal(value)))
            __save_graph(graph, output_file)


def read_classes_normalized_unit(ttl_file):
    """
    loads the units from a normalized ontology and no references to OM 2 where mase there.

    :param str ttl_file: path to the ontology file to load

    :returns: dictionary with the key as the key and the units as the values
    :rtype: OrderedDict
    """
    graph = __create_rdf_graph([ttl_file])

    classes = __get_local_classes(graph, [ttl_file])
    units_dict = {}

    for class_uri in classes:
        # get units
        predicate = OP.OM_ONT['base_unit']
        base_units_uri = __get_class_object(graph, class_uri, predicate)
        base_units = [__get_entity_name(item.split('/')[-1]).lower()
                      if validators.url(item) else str(item)
                      for item in base_units_uri]

        predicate = OP.OM_ONT['prefixed_unit']
        prefixed_units_uri = __get_class_object(graph, class_uri, predicate)
        prefixed_units = [__get_entity_name(item.split('/')[-1]).lower()
                          if validators.url(item) else str(item)
                          for item in prefixed_units_uri]

        predicate = OP.OM_ONT['base_symbol']
        base_symbol_uri = __get_class_object(graph, class_uri, predicate)
        base_symbols = [__get_entity_name(item.split('/')[-1]).lower()
                        if validators.url(item) else str(item)
                        for item in base_symbol_uri]

        predicate = OP.OM_ONT['symbol']
        prefixed_symbol_uri = __get_class_object(graph, class_uri, predicate)
        prefixed_symbols = [__get_entity_name(item.split('/')[-1]).lower()
                            if validators.url(item) else str(item)
                            for item in prefixed_symbol_uri]
        units_dict[__get_entity_name(class_uri)] = {"base_units": list(dict.fromkeys(base_units)),
                                                    "prefixed_units": list(dict.fromkeys(prefixed_units)),
                                                    "base_symbols": list(dict.fromkeys(base_symbols)),
                                                    "prefixed_symbols": list(dict.fromkeys(prefixed_symbols))}

    return OrderedDict(sorted(units_dict.items()))


def get_classes_unit(ttl_file, om_file_path):
    """
    loads the units from the ontology with the help of the OM 2.0.

    :param str ttl_file: path to the ontology file to load
    :param str om_file_path: path to OM 2.0

    :returns: dictionary with the key as the key and the units as the values
    :rtype: OrderedDict
    """
    graph = __create_rdf_graph([ttl_file])

    classes = __get_local_classes(graph, [ttl_file])

    # loading the file takes 5 seconds
    om_graph = __create_rdf_graph([om_file_path])

    units_dict = {}

    for class_uri in classes:
        # get units
        predicate = OP.OM_ONT['base_unit']
        base_units_uri = __get_class_object(graph, class_uri, predicate)
        base_units = [__get_entity_name(item.split('/')[-1]).lower()
                      if validators.url(item) else str(item)
                      for item in base_units_uri]

        predicate = OP.OM_ONT['prefixed_unit']
        prefixed_units_uri = __get_class_object(graph, class_uri, predicate)
        prefixed_units = [__get_entity_name(item.split('/')[-1]).lower()
                          if validators.url(item) else str(item)
                          for item in prefixed_units_uri]
        base_symbols = []
        # get symbols of units
        for unit in base_units_uri:
            if not validators.url(unit):  # if no symbol found, use the unit name
                base_symbols.append(str(unit))
                continue
            predicate = OP.OM_ONT['symbol']
            obj = __get_class_object(om_graph, unit, predicate)
            base_symbols += [str(item) for item in obj]

        prefixed_symbols = []
        for unit in prefixed_units_uri:
            if not validators.url(unit):  # if no symbol found, use the unit name
                prefixed_symbols.append(str(unit))
                continue

            predicate = OP.OM_ONT['symbol']
            obj = __get_class_object(om_graph, unit, predicate)
            prefixed_symbols += [str(item) for item in obj]

        units_dict[__get_entity_name(class_uri)] = {"base_units": list(dict.fromkeys(base_units)),
                                                    "prefixed_units": list(dict.fromkeys(prefixed_units)),
                                                    "base_symbols": list(dict.fromkeys(base_symbols)),
                                                    "prefixed_symbols": list(dict.fromkeys(prefixed_symbols))}

    return OrderedDict(sorted(units_dict.items()))


def load_ontology_classes(filename):
    """
    Function to get all classes from an ontology.

    :param str filename: a file_path of the ontology.

    :returns: an rdfgraph and an array of classes in the ontology
    :rtype: rdfgraph, list of rdf object
    """
    graph = __create_rdf_graph([filename])
    classes = __get_local_classes(graph, [filename])
    return graph, classes


def list_classes_labels(graph, classes, normalized):
    """
    Function to get labels from all classes of an ontology.

    :param rdfgraph graph: a rdf graph of the ontology.
    :param [rdf classes] classes: all classes of the ontology.
    :param bool normalized: determines whether the normalized ontology is used

    :returns: list of all labels of each class
    :rtype: array of array of string
    """

    def get_objects_by_predicate(graph, classes, predicate):
        return [__get_class_object(graph, cl, predicate) for cl in classes]

    entities_labels = []

    labels = get_objects_by_predicate(graph, classes,
                                      OP.WIKIDATA_ONT['labels'])

    alt_labels = get_objects_by_predicate(graph, classes,
                                          OP.WIKIDATA_ONT['alt_label'])

    see_also = get_objects_by_predicate(graph, classes,
                                        OP.WIKIDATA_ONT['see_also'])

    common_cat = get_objects_by_predicate(graph, classes,
                                          OP.WIKIDATA_ONT['common_category'])

    entities = [__get_entity_name(class_uri) for class_uri in classes]

    i = 0
    for ent in entities:
        ent_label = [ent]
        ent_label += [str(l) for l in labels[i] if str(l) not in ent_label]
        ent_label += [str(l) for l in alt_labels[i] if str(l) not in ent_label]
        ent_label += [str(l) for l in see_also[i] if str(l) not in ent_label]
        ent_label += [str(l) for l in common_cat[i] if str(l) not in ent_label]
        if not normalized:
            ent_label += [l.capitalize() for l in ent_label
                          if l.capitalize() not in ent_label]
            ent_label += [l.title() for l in ent_label
                          if l.title() not in ent_label]
            ent_label += [l.lower() for l in ent_label
                          if l.lower() not in ent_label]
            ent_label += [l.upper() for l in ent_label
                          if l.upper() not in ent_label]

        entities_labels.append(ent_label)
        i += 1
    entities_labels.sort(key=lambda x: x[0])
    return entities_labels


def __build_all_units_list(units_onto):
    units_list = []
    for entry, entry_dict in units_onto.items():
        key_main_unit = entry_dict['base_units']
        key_units = entry_dict['prefixed_units']
        for key_unit in key_units:
            if key_unit not in units_list:
                units_list.append(key_unit)
        if key_main_unit and key_main_unit[0] not in units_list:
            units_list.append(key_main_unit[0])
    return list(set(units_list))


def __build_all_symbols_list(symbols):
    symbols_list = []
    for entry, entry_dict in symbols.items():
        key_main_symbol = entry_dict['base_symbols']
        key_symbols = entry_dict['prefixed_symbols']
        for key_symbol in key_symbols:
            if key_symbol not in symbols_list:
                symbols_list.append(key_symbol)
        if key_main_symbol and key_main_symbol[0] not in symbols_list:
            symbols_list.append(key_main_symbol[0])
    return list(set(symbols_list))


def __get_entity_name(class_uri):
    entity_name = class_uri[class_uri.rfind('#') + 1:]
    spaced_name = TU.replace_camelcase_with_space(entity_name)
    spaced_name = re.sub(nlp_assets.REGEX['non_alpha_num'],
                         nlp_assets.SPACE, spaced_name)
    return spaced_name


# Graph handlers
def __create_rdf_graph(files):
    graph = Graph()
    for filename in files:
        file_format = filename.split('.')[-1]
        # if the format is rdf, change the text
        if file_format == 'rdf':
            file_format = 'application/rdf+xml'

        graph.parse(filename, format=file_format)
    return graph


def __get_onto_base_namespace(input_file, start_tag='@prefix : <', end_tag='#> .'):
    # rdflib cannot read the prefix, the namespace must be parsed directly
    ont_text = CF.read_from_file(input_file).lower()
    namespace = ont_text[ont_text.find(start_tag) + len(start_tag):
                         ont_text.find(end_tag)]
    return namespace


def __get_local_classes(graph, input_files):
    namespace = []
    for file in input_files:
        namespace.append(__get_onto_base_namespace(file))

    try:
        classes = [str(s) for s, p, o in graph.triples((None, RDF.type, OWL.Class))
                   for ns in namespace if s.startswith(ns)]
        return classes

    except Exception as ex:
        CF.log('get_local_classes exception: > ' + str(ex))
    return []


def __save_graph(graph, filename):
    file_format = filename.split('.')[-1]
    graph.serialize(destination=filename, format=file_format)


def __get_class_object(graph, class_uri, predicate):
    res = [o for s, p, o in graph.triples((URIRef(class_uri), URIRef(predicate), None))]
    return res
