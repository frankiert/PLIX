"""
Class for StanzaSimpleUnitMatcher
"""
from evaluation.spacy_.spacy_simple_row_evaluation import SpacySimpleRowMatcher
from evaluation.spacy_.spacy_simple_table_units_evaluation import SpacySimpleTableUnitMatcher


class StanzaSimpleUnitMatcher(SpacySimpleRowMatcher, SpacySimpleTableUnitMatcher):
    def __init__(self, keys, units, tables):
        super().__init__(keys, units, tables, stanza=True)

    def _extract_kvu(self):
        results = []
        files = self.tables["Filename"]
        tables = self.tables["NormalizedTableData"]
        for file, table in zip(files, tables):
            for row in table[0]:  # just one table per document
                str_table = "; ".join([cell for cell in row])
                table_result = self._match_dependencies(str_table)
                formatted_match = self._format_results(table_result)
                # on row level to remove duplicates
                for match in formatted_match:
                    main_key = self._get_main_key(match[0])
                    if SpacySimpleTableUnitMatcher._is_valid_kvu(self, match, main_key):
                        results.append([file, main_key.lower(), match[1], match[2]])
        return results

    def do_extraction(self):
        SpacySimpleRowMatcher._prepare_ner(self)
        SpacySimpleRowMatcher._add_match_pattern(self)
        return self._extract_kvu()
