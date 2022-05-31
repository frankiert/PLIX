"""
Holds all constants related to NLP methods.
"""
########################################
# TEXT CLASSIFICATION                  #
########################################
TEXT_CLASSES = [['asynchronous machine'], ['synchronous machine'], ['outer rotor machine'], ['radial magnetization'],
                ['interior permanent magnets', 'IPM'],
                ['surface mounted permanent magnets', 'SPM', 'surface-mounted PM', 'SMPM',
                 'surface mounted permanent magnet'], ['slotless stator']]
########################################
# NORMALIZATION                        #
########################################
DOMAIN_WORDS = ['cos', 'sin', '%', 'ddtc', 'v', 'a', 'PST', 'PMT', 'PBT', 'i', 'x', '[', ']', '(', ')', '+', '-',
                '*', '/', '=', 'Ω']  # add to vocabulary as domain words
ROW_MULTIPLE_KEYS_DELIMITER = '/'  # if different from / change related regex below
REPLACE_PATTERNS = {
    '—': '-',
    '–': '-',
    '’': '\'',
    'I': 'I',
    'N-m': 'nm',
    'min-1': 'rpm',
    'min1': 'rpm',
    'r/min': 'rpm',
    'r.p.m.': 'rpm',
    'r.p . m': 'rpm',
    'ohm': 'o',
    '\xa0': ' ',
    '\t': ' '
}
# enable as needed
GREEK = {
    # 'α': 'alpha',
    # 'β': 'beta',
    # 'γ': 'gamma',
    # 'δ': 'delta',
    # 'ε': 'epsilon',
    # ' ζ': 'zeta',
    # 'η': 'eta',
    # 'θ': 'theta',
    # 'ι': 'iota',
    # 'κ': 'kappa',
    # 'λ': 'lambda',
    # 'μ': 'micro',
    # 'ν': 'nu',
    # 'ξ': 'xi',
    # 'π': 'pi',
    # 'ρ': 'rho',
    # 'σ': 'sigma',
    # 'τ': 'tau',
    # 'φ': 'phi',
    # 'χ': 'chi',
    # 'ψ': 'psi',
    # 'ω': 'Ω',
    # 'Ω': 'ohm'
}
########################################
# DATA EXTRACTION                      #
########################################
# cut all text following these words
TEXT_CUT_KEYWORDS = ['Acknowledgement', 'ACKNOWLEDGEMENT', 'Acknowledgment', 'ACKNOWLEDGMENT', 'Literature',
                     'LITERATURE', 'References', 'REFERENCES', 'Bibliography', 'BIBLIOGRAPHY']
TABLE_FILTER = ['Algorithm \d+', 'doi', 'e-mail', 'University']  # words to filter complete table
########################################
# REGULAR EXPRESSIONS                  #
########################################
REGEX = {
    'non_alpha_num': r'[^A-Za-z0-9.,]+',
    'multi_spaces': r'\s\s+',
    'newline': r'[\r?\n|\r]',
    'camel_case': '([a-z])([A-Z])',  # normalCamel
    'camel_case2': '([A-Z])([A-Z][a-z])',  # camelAFTERSpecialName
    'replace_space': r'\g<1> \g<2>',
    'line_hyphen': r'(?<=\w)-\s?\r?\n(?=\w)',
    'square_bracket_citation': r'\[[\d+\s]+?\]',
    'cid': r'\((\bcid:\b)\d+\)',
    'tokenize': r'\w+[.|,]?\w*|[^\w]',
    'possible_multiple_entities': r'^[a-zA-Z]+( [a-zA-Z]+)*\s?[\[\(\,]?\s?[\w]*\s?[\]\)]?\s?\/\s?[a-zA-Z]+'
                                  r'( [a-zA-Z]+)*\s?[\[\(\,]?\s?[\w]*\s?[\]|\)]?$',
    'number': r'\b(-?\d+\.\d+)$|^(-?\d+)%?',
    'regex_number': r"[-|+|<|>|=|\s]*\s?\d+[,|.]?\d*",
    'regex_e_number': r"[-|+|<|>|=|\s]*\s?\d+[,|.]?\d*e\-?\d*",
    'regex_range': r"\s?-{0,2}\s?",
    'regex_unit': r"[\[|\(|,]{1,2}\s?[\w|\%|\/|\s]*\s?[\]|\)]?",
    'regex_unit_optional': r"\s?[\[|\(|,]{0,2}\s?[\w|\%|\/|\s]*\s?[\]|\)]?",
    'regex_dimension': r"\s?x\s?",
    'regex_multiple': r"\s?\/\s?",
    'regex_start': r"(",
    'regex_end': r")",
    'regex_count_03': r"{0,3}",
    'regex_count_1': r"+",
    'regex_count_0': r"?",
    'regex_count_mult': r"*"

}

########################################
# REGULAR EXPRESSIONS VALUE EXTRACTION #
########################################
REGEX_NUMBER = r"([-+><=~\s]){0,3}\s*(\b[0-9]{1,3}(,[0-9]{3})*(\.[0-9]*)?|\.[0-9]+)\s*([eE^]\s*[-+]?\s*[0-9]+\b)?"
REGEX_RANGE = r"(-|to|\.{3})"
REGEX_E_NUMBER = r"([-+><=~\s]){0,3}\s*(\b[0-9]{1,3}(,[0-9]{3})*(\.[0-9]*)?|\.[0-9]+)\s*([eE]\s*[-+]?\s*[0-9]+\b)"
REGEX_DIMENSION = r"[xX]"
REGEX_OPTIONAL_NONCAP_SPACE = r"(?=\s)?"
REGEX_ONE_UNIT = r"(\%|[a-zA-Z](\w+\s*(\^\s?[+-]?\s*[0-9]+)?)?)"
REGEX_COMPOUND_UNIT = fr"{REGEX_ONE_UNIT}\s*(\/\s*{REGEX_ONE_UNIT})?"
REGEX_UNIT = fr"{REGEX_OPTIONAL_NONCAP_SPACE}[\[\(,]?\s*{REGEX_COMPOUND_UNIT}\s*[\]\)]?{REGEX_OPTIONAL_NONCAP_SPACE}"
REGEX_RANGE_NUMBER = fr"{REGEX_NUMBER}(\s*{REGEX_RANGE}\s*{REGEX_NUMBER})?"
REGEX_NUMBER_AND_UNIT = fr"{REGEX_NUMBER}\s*{REGEX_UNIT}"
REGEX_3D_VALUE = fr"{REGEX_RANGE_NUMBER}(\s*[xX]\s*{REGEX_RANGE_NUMBER})" + r"{0,2}"

# number [unit] - number[unit]
REGEX_range_number = REGEX['regex_number'] + REGEX['regex_unit_optional'] + REGEX['regex_start'] + REGEX_RANGE + \
                     REGEX['regex_number'] + REGEX['regex_unit_optional'] + REGEX['regex_end'] + REGEX['regex_count_0']
# number [unit] - number[unit]
REGEX_range_just_number = REGEX['regex_number'] + REGEX['regex_start'] + REGEX_RANGE + \
                          REGEX['regex_number'] + REGEX['regex_end'] + REGEX['regex_count_0']
# (number [unit] - number[unit]) / (number [unit] - number[unit])
REGEX_whole_multiple = REGEX_range_number + REGEX['regex_start'] + REGEX['regex_multiple'] + \
                       REGEX_range_number + REGEX['regex_end'] + REGEX['regex_count_mult']
# (number [unit] - number[unit]) x (number [unit] - number[unit]) x (number [unit] - number[unit])
REGEX_whole_dimension = REGEX_range_number + REGEX['regex_start'] + REGEX['regex_dimension'] + \
                        REGEX_range_number + REGEX['regex_end'] + REGEX['regex_count_03']
REGEX_whole_dimension_numbers = REGEX_range_just_number + REGEX['regex_start'] + REGEX['regex_dimension'] + \
                                REGEX_range_just_number + REGEX['regex_end'] + REGEX['regex_count_03']
# covers everything a value could be from 1 to
# 0.5 mm - 34 mm x 12.0-45 mm x 5 mm / 0.5 mm x 12 mm x 5 mm / 0.5 mm x 12 mm x 5 mm / 0.5 mm x 12 mm x 5 mm
REGEX_whole_dimension_multiple_all = REGEX_whole_dimension + REGEX['regex_start'] + REGEX['regex_multiple'] + \
                                     REGEX_whole_dimension + REGEX['regex_end'] + REGEX['regex_count_mult']
# / is mandatory
REGEX_whole_dimension_multiple = REGEX_whole_dimension + REGEX['regex_start'] + REGEX['regex_multiple'] + \
                                 REGEX_whole_dimension + REGEX['regex_end'] + REGEX['regex_count_1']

########################################
# OTHER                                #
########################################
INDENT = '\t'
DELIMITER = '\t'
NEWLINE = '\n'
SPACE = ' '
