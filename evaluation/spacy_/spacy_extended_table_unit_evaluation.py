"""
Class for SpacyExtendedTableUnitMatcher
"""
from evaluation.spacy_.spacy_extended_table_evaluation import SpacyExtendedTableMatcher
from evaluation.spacy_.spacy_simple_table_units_evaluation import SpacySimpleTableUnitMatcher


class SpacyExtendedTableUnitMatcher(SpacyExtendedTableMatcher, SpacySimpleTableUnitMatcher):
    def __init__(self, keys, units, tables):
        super().__init__(keys, units, tables)

    def do_extraction(self):
        SpacyExtendedTableMatcher._prepare_ner(self)
        SpacyExtendedTableMatcher._add_match_pattern(self)
        return SpacySimpleTableUnitMatcher._extract_kvu(self)
