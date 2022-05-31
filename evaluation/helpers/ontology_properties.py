"""
Data structure that defines properties for ontologies.
"""

WIKIDATA_ONT = {
    'labels': 'http://www.w3.org/2000/01/rdf-schema#label',
    'alt_label': 'http://www.w3.org/2004/02/skos/core#altLabel',
    'common_category': 'http://www.w3.org/2004/02/skos/core#altLabel',
    'description': 'http://schema.org/description',
    'about': 'http://schema.org/about',
    'instance_of': 'http://www.w3.org/2000/01/rdf-schema#type',
    'subclass_of': 'http://www.w3.org/2000/01/rdf-schema#subClassOf',
    'part_of': 'http://www.w3.org/2000/01/rdf-schema#member',
    'same_as': 'http://www.w3.org/2000/01/rdf-schema#isDefinedBy',
    'described_by': 'http://www.w3.org/2000/01/rdf-schema#isDefinedBy',
    'see_also': 'http://www.w3.org/2000/01/rdf-schema#seeAlso',
    'disjoint': 'http://www.w3.org/2002/07/owl#disjointWith',
    'equivalent_class': 'http://www.w3.org/2002/07/owl#equivalentClass'
}

OM_ONT = {
    'common_unit': 'http://www.ontology-of-units-of-measure.org/resource/om-2/commonlyHasUnit',
    'base_unit': 'http://www.ontology-of-units-of-measure.org/resource/om-2/Unit',
    'prefixed_unit': 'http://www.ontology-of-units-of-measure.org/resource/om-2/PrefixedUnit',
    'labels': 'http://www.w3.org/2000/01/rdf-schema#label',
    'alt_label': 'http://www.ontology-of-units-of-measure.org/resource/om-2/alternativeLabel',
    'symbol': 'http://www.ontology-of-units-of-measure.org/resource/om-2/symbol',
    'base_symbol': 'http://www.ontology-of-units-of-measure.org/resource/om-2/alternativeSymbol'
}
