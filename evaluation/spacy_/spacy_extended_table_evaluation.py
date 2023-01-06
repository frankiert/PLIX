"""
Class for SpacyExtendedTableMatcher
"""
from evaluation.spacy_.spacy_simple_table_evaluation import SpacySimpleTableMatcher

KVU_DEPENDENCY_MATCH_PATTERN = [
    {
        "RIGHT_ID": "key_found",
        "RIGHT_ATTRS": {"ENT_TYPE": 'KEYWORD'}
    },
    {
        "LEFT_ID": "key_found",
        "REL_OP": ".*",
        "RIGHT_ID": "key_value",
        "RIGHT_ATTRS": {"POS": "NUM"},
    },
    {
        "LEFT_ID": "key_value",
        "REL_OP": ".*",
        "RIGHT_ID": "value_unit",
        "RIGHT_ATTRS": {"ENT_TYPE": 'UNIT'},
    }
]

KUV_DEPENDENCY_MATCH_PATTERN = [
    {
        "RIGHT_ID": "key_found",
        "RIGHT_ATTRS": {"ENT_TYPE": 'KEYWORD'}
    },
    {
        "LEFT_ID": "key_found",
        "REL_OP": ".*",
        "RIGHT_ID": "key_unit",
        "RIGHT_ATTRS": {"ENT_TYPE": 'UNIT'}
    },
    {
        "LEFT_ID": "key_unit",
        "REL_OP": ".*",
        "RIGHT_ID": "unit_value",
        "RIGHT_ATTRS": {"POS": "NUM"}
    }
]

UKV_DEPENDENCY_MATCH_PATTERN = [
    {
        "RIGHT_ID": "unit_found",
        "RIGHT_ATTRS": {"ENT_TYPE": 'UNIT'}
    },
    {
        "LEFT_ID": "unit_found",
        "REL_OP": ".*",
        "RIGHT_ID": "unit_key",
        "RIGHT_ATTRS": {"ENT_TYPE": 'KEYWORD'}
    },
    {
        "LEFT_ID": "unit_key",
        "REL_OP": ".*",
        "RIGHT_ID": "key_value",
        "RIGHT_ATTRS": {"POS": "NUM"}
    }
]


class SpacyExtendedTableMatcher(SpacySimpleTableMatcher):
    def __init__(self, keys, units, tables, stanza=False):
        super().__init__(keys, units, tables, stanza)

    def _add_match_pattern(self):
        self.matcher.add("KVU", [KVU_DEPENDENCY_MATCH_PATTERN])
        self.matcher.add("KUV", [KUV_DEPENDENCY_MATCH_PATTERN])
        self.matcher.add("UKV", [UKV_DEPENDENCY_MATCH_PATTERN])

    def _format_results(self, matches):
        formatted_results = []
        for match in matches:
            formatted_match = []
            match_id, token_ids = match
            matched_pattern = self.nlp.vocab.strings[match_id]
            if matched_pattern == "KVU":
                pass
            elif matched_pattern == "KUV":
                token_ids = [token_ids[0], token_ids[2], token_ids[1]]
            else:  # UKV
                token_ids = [token_ids[1], token_ids[2], token_ids[0]]
            for i in token_ids:
                formatted_match.append(self.doc[i].text)
            formatted_results.append(formatted_match)
        return formatted_results

    def do_extraction(self):
        self._prepare_ner()
        self._add_match_pattern()
        return self._extract_kvu()
