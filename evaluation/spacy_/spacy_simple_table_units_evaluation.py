"""
Class for SpacySimpleTableUnitMatcher
"""
from evaluation.spacy_.spacy_simple_table_evaluation import SpacySimpleTableMatcher, _table_to_str


class SpacySimpleTableUnitMatcher(SpacySimpleTableMatcher):
    def __init__(self, keys, units, tables, stanza=False):
        super().__init__(keys, units, tables, stanza)

    def _is_valid_kvu(self, kvu_tuple, main_key):
        allowed_units = self.units[main_key]['prefixed_units']
        allowed_symbols = self.units[main_key]['prefixed_symbols']
        if kvu_tuple[2] in allowed_units or kvu_tuple[2] in allowed_symbols:
            return True
        return False

    def _extract_kvu(self):
        results = []
        files = self.tables["Filename"]
        tables = self.tables["NormalizedTableData"]
        for file, table in zip(files, tables):
            str_table = _table_to_str(table[0])
            table_result = self._match_dependencies(str_table)
            formatted_match = self._format_results(table_result)
            for match in formatted_match:
                main_key = self._get_main_key(match[0])
                if self._is_valid_kvu(match, main_key):
                    results.append([file, main_key.lower(), match[1], match[2]])
        return results

    def do_extraction(self):
        self._prepare_ner()
        self._add_match_pattern()
        return self._extract_kvu()
