"""
Class for SpacyExtendedRowMatcher.
"""
from evaluation.spacy_.spacy_extended_table_evaluation import SpacyExtendedTableMatcher
from evaluation.spacy_.spacy_simple_row_evaluation import SpacySimpleRowMatcher


class SpacyExtendedRowMatcher(SpacyExtendedTableMatcher, SpacySimpleRowMatcher):
    def __init__(self, keys, units, tables):
        super().__init__(keys, units, tables)

    def do_extraction(self):
        SpacyExtendedTableMatcher._prepare_ner(self)
        SpacyExtendedTableMatcher._add_match_pattern(self)
        return SpacySimpleRowMatcher._extract_kvu(self)
