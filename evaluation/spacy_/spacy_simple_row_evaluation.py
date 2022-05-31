"""
Class for SpacySimpleRowMatcher
"""
from evaluation.spacy_.spacy_simple_table_evaluation import SpacySimpleTableMatcher


class SpacySimpleRowMatcher(SpacySimpleTableMatcher):
    def __init__(self, keys, units, tables):
        super().__init__(keys, units, tables)

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
                    results.append([file, self._get_main_key(match[0]).lower(), match[1], match[2]])
        return results

    def do_extraction(self):
        self._prepare_ner()
        self._add_match_pattern()
        return self._extract_kvu()
