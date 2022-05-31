"""
Class for SpacyExtendedRowUnitMatcher
"""
from evaluation.spacy_.spacy_extended_table_evaluation import SpacyExtendedTableMatcher
from evaluation.spacy_.spacy_simple_row_units_evaluation import SpacySimpleRowUnitMatcher


class SpacyExtendedRowUnitMatcher(SpacyExtendedTableMatcher, SpacySimpleRowUnitMatcher):
    def __init__(self, keys, units, tables):
        super().__init__(keys, units, tables)

    def do_extraction(self):
        SpacyExtendedTableMatcher._prepare_ner(self)
        SpacyExtendedTableMatcher._add_match_pattern(self)
        return SpacySimpleRowUnitMatcher._extract_kvu(self)
