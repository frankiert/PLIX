"""
Helper script to normalize a ttl ontology and then save the keywords and units seperately.
Can be used as input for ArtTabGen.
"""
import json
import os

import evaluation.helpers.ontology_utils as OU
from plix import normalize_keyword_dk, normalize_unit_dk


def load_ontos(onto_file, unit_onto_path, om_file_path):
    graph, classes = OU.load_ontology_classes(onto_file)
    unit_onto = OU.get_classes_unit(unit_onto_path, om_file_path)
    keyword_onto = OU.list_classes_labels(graph, classes, False)
    return keyword_onto, unit_onto


if __name__ == "__main__":
    key_onto_path = "star-sensor-unit_disambiguated.ttl"
    unit_onto_path = "star-sensor-unit_disambiguated.ttl"
    core_onto_file = "core-unit_disambiguated.ttl"
    om_path = "om-2.0.rdf"
    out_path = "data\\"

    keys, units = load_ontos(key_onto_path, unit_onto_path, om_path)
    core_keys, core_units = load_ontos(core_onto_file, core_onto_file, om_path)

    keys = normalize_keyword_dk(keys)
    units = normalize_unit_dk(units)
    core_keys = normalize_keyword_dk(core_keys)
    core_units = normalize_unit_dk(core_units)
    OU.unit_ontology_update(units, keys, [key_onto_path],
                            "star-sensor-unit_disambiguated_normalized.ttl")
    OU.unit_ontology_update(core_units, core_keys, [core_onto_file],
                            "core-unit_disambiguated_normalized.ttl")

    units.update(core_units)
    keys += core_keys
    with open(os.path.join(out_path, "units_star_sensor.json"), "w+") as f:
        json.dump(units, indent=4, sort_keys=True, fp=f)

    with open(os.path.join(out_path, "keywords_star_sensor.txt"), "w+") as f2:
        for line in keys:
            f2.write(",".join(word for word in line))
            f2.write("\n")
