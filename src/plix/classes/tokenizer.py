"""
This class is for tokeninzing text and holds a vocabulary.

Modified from:
S. Boening, Assessing the State-of-the-art for Source-Code Suggestions, Master's Thesis,
Bauhaus University Weimar, Weimar, June 2020.
Based on the tokenizer from Huggingface Transformer
"""

import collections
import os
import re
from itertools import chain

import nltk

import plix.nlp_assets as nlp_assets

try:
    nltk.data.find("words")
except LookupError:
    nltk.download("words", quiet=True)
try:
    nltk.data.find("omw-1.4")
except LookupError:
    nltk.download("omw-1.4", quiet=True)
try:
    nltk.data.find("punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


def whitespace_tokenize(text):
    """
    Runs basic whitespace cleaning and splitting on a text.

    :param str text:

    :returns: the tokenized text
    :rtype: list
    """
    text = text.strip()
    if not text:
        return []
    tokens = text.split()
    return tokens


def tokenize(text):
    """
    Tokenizes a text with nltk.word_tokenize.

    :param str text:

    :returns: the tokenized text
    :rtype: list
    """
    data = nltk.word_tokenize(text)
    for i, word in enumerate(data):
        data[i] = re.findall(nlp_assets.REGEX['tokenize'], data[i], re.UNICODE)
    return list(chain.from_iterable(data))


def load_vocab(vocab_file):
    """
    Loads a vocabulary file into a dictionary.

    :param str vocab_file: the file to load

    :returns: the loaded vocabulary
    :rtype: collections.OrderedDict
    """
    vocab = collections.OrderedDict()
    if os.path.exists(vocab_file):
        with open(vocab_file, "r", encoding="utf-8") as reader:
            tokens = reader.read()
        tokens = tokens.split("\n")
        i = 0
        for index, token in enumerate(tokens):
            if token not in vocab:
                vocab[token] = i
                i += 1
    return vocab


class Tokenizer:
    def __init__(self, vocab_file):
        super(Tokenizer, self).__init__()
        self.path = vocab_file
        self.vocab = load_vocab(self.path)
        self.unk_token = "[UNK]"
        self.ids_to_tokens = collections.OrderedDict([(ids, tok) for tok, ids in self.vocab.items()])

    def generate_vocab(self, to_add):
        """
        Generates an English vocabulary and saves it to a file.

        :param list or set to_add: list of words to add to the dictionary
        """
        # set of all english words from nltk
        english = set(w.lower() for w in nltk.corpus.words.words())
        new_vocab = sorted(list(set.union(english, set(to_add))))  # cast to set to remove duplicates
        # write vocabulary to file to load later
        with open(self.path, "w+", encoding="utf-8") as f:
            f.write("{}\n{}\n{}\n".format("[UNK]", "[CLS]", "[SEP]"))
            for word in new_vocab:
                f.write("%s\n" % word)

    def refresh_vocab(self):
        """
        Loads the vocabulary file and updates the internal vocabulary of the tokenizer.
        """
        if self.path:
            self.vocab = load_vocab(self.path)
        self.ids_to_tokens = collections.OrderedDict([(ids, tok) for tok, ids in self.vocab.items()])

    def convert_token_to_id(self, token):
        """
        Converts a token (str/unicode) in an id_ using the vocab.

        :param str token: the token

        :returns: the id of the token
        :rtype: int
        """
        return self.vocab.get(token, self.vocab.get(self.unk_token))

    def convert_id_to_token(self, index):
        """
        Converts an index (integer) in a token (string/unicode) using the vocab.

        :param int index: index of a token

        :returns: the token
        :rtype: str
        """
        return self.ids_to_tokens.get(index, self.unk_token)

    def convert_tokens_to_ids(self, tokens):
        """
        Converts a single token, or a sequence of tokens, (str) in a single integer id
        (resp. a sequence of ids), using the vocabulary.
        :param str or list tokens: tokens to be converted into ids

        :returns: id(s) of token(s)
        :rtype: int or list
        """
        if tokens is None:
            return None

        if isinstance(tokens, str):
            return self.convert_token_to_id(tokens)

        ids = []
        for token in tokens:
            ids.append(self.convert_token_to_id(token))
        return ids

    def convert_ids_to_tokens(self, ids, skip_special_tokens=False):
        """
        Converts a single index or a sequence of indices (integers) in a token
        (resp.) a sequence of tokens (str), using the vocabulary and added tokens.

        :param int or list ids: ids to be converted back into tokens
        :param bool skip_special_tokens: Don't decode special tokens (self.all_special_tokens). Default: False

        :returns ids of tokens
        :rtype: str or list
        """
        if isinstance(ids, int):
            return self.convert_id_to_token(ids)
        tokens = []
        for index in ids:
            index = int(index)
            if skip_special_tokens:
                continue
            tokens.append(self.convert_id_to_token(index))
        return tokens

    def is_token_in_vocab(self, token):
        """
        Checks whether a token is in the vocabulary

        :param str token: the token to check

        :returns: true if token is in vocabulary
        :rtype: bool
        """
        return token in self.vocab

    def get_vocab_len(self):
        """
        Returns the length of the vocabulary.

        :returns: length
        :rtype: int
        """
        return len(self.ids_to_tokens)
