"""
Class for SpacySimpleTableMatcher
"""
from itertools import chain

import spacy
import spacy_stanza
import stanza
from spacy.matcher import DependencyMatcher

DEPENDENCY_MATCH_PATTERN = [
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


def _table_to_str(table):
    str_table = ""
    for row in table:
        str_row = "; ".join([cell for cell in row])
        str_table += " " + str_row
    return str_table


class SpacySimpleTableMatcher(object):
    def __init__(self, keys, units, tables, stanza_=False):
        self.keywords = keys
        self.units = units
        self.tables = tables
        if not stanza_:
            self.nlp = spacy.load("en_core_web_sm")
        else:
            self.stanza = stanza.download("en")
            self.nlp = spacy_stanza.load_pipeline("en")
        self.ruler = self.nlp.add_pipe("entity_ruler")
        self.matcher = DependencyMatcher(self.nlp.vocab)
        self.doc = None
        self.matches = None

    def __add_unit_entities(self, patterns):
        units_done = []
        for entry, entry_dict in self.units.items():
            for unit_symbol, unit_symbol_list in entry_dict.items():
                for unit in unit_symbol_list:
                    if unit not in units_done:
                        units_done.append(unit)
                        unit = unit.split(" ")
                        if len(unit) > 1:
                            tokens = []
                            for token in unit:
                                tokens.append({"LOWER": token.lower()})
                            patterns.append({"label": "UNIT", "pattern": tokens})
                        else:
                            patterns.append({"label": "UNIT", "pattern": unit[0].lower()})
        return patterns

    def __add_keyword_entities(self, patterns):
        keys = list(chain.from_iterable(self.keywords))
        keys_done = []
        for k in keys:
            k = k.lower()
            if k not in keys_done:
                keys_done.append(k)
                k = k.split(" ")
                if len(k) > 1:
                    tokens = []
                    for token in k:
                        tokens.append({"LOWER": token})
                    patterns.append({"label": "KEYWORD", "pattern": tokens})
                else:
                    patterns.append({"label": "KEYWORD", "pattern": k[0].lower()})
        return patterns

    def _prepare_ner(self):
        patterns = []
        patterns = self.__add_unit_entities(patterns)
        patterns = self.__add_keyword_entities(patterns)
        self.ruler.add_patterns(patterns)

    def _add_match_pattern(self):
        self.matcher.add("KVU", [DEPENDENCY_MATCH_PATTERN])

    def __ner_text(self, text):
        self.doc = self.nlp(text)
        with self.doc.retokenize() as retokenizer:
            for ent in self.doc.ents:
                retokenizer.merge(self.doc[ent.start:ent.end])

    def _match_dependencies(self, table):
        self.__ner_text(table)
        matches = self.matcher(self.doc)
        return matches

    def _format_results(self, matches):
        formatted_results = []
        for match in matches:
            formatted_match = []
            match_id, token_ids = match
            for i in token_ids:
                formatted_match.append(self.doc[i].text)
            formatted_results.append(formatted_match)
        return formatted_results

    def _get_main_key(self, synonym):
        for synonyms in self.keywords:
            if synonym in synonyms:
                return synonyms[0]
        return ""

    def _extract_kvu(self):
        results = []
        files = self.tables["Filename"]
        tables = self.tables["NormalizedTableData"]
        for file, table in zip(files, tables):
            str_table = _table_to_str(table[0])
            table_result = self._match_dependencies(str_table)
            formatted_match = self._format_results(table_result)
            for match in formatted_match:
                results.append([file, self._get_main_key(match[0]).lower(), match[1], match[2]])
        return results

    def do_extraction(self):
        self._prepare_ner()
        self._add_match_pattern()
        return self._extract_kvu()
