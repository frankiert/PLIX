"""
This class contains functionality to extract data from PDF files.
A dataframe holding all extracted data is created.

The result has the following format:

+-----------+------------------+------------------+---------------------+-------------------------------+-----------------------------------------------+------------------------------+-----------------+-----------------------------------------------------+------------------------------------------+------------------------------------------------+--------------------+-------------------+----------------+
|   index   |     Filename     |     FullPath     |       Category      |         Classification        |              Classification Count             |           TableData          |     Metadata    |                       allText                       |                 cleanText                |                 MeaningfulText                 |        Text        |    cleanOCRText   |    OCRedText   |
+===========+==================+==================+=====================+===============================+===============================================+==============================+=================+=====================================================+==========================================+================================================+====================+===================+================+
| row index | name of pdf file | path to pdf file | category of the pdf | list of classification labels | list with occurences of classification labels | list of extracted table data | metadata of pdf | finished, extracted text, pages are joined together | cleaned-up text from the text extraction | text chosen between cleanOCRText and cleanText | raw extracted text | cleaned OCRedText | raw OCRed text |
+-----------+------------------+------------------+---------------------+-------------------------------+-----------------------------------------------+------------------------------+-----------------+-----------------------------------------------------+------------------------------------------+------------------------------------------------+--------------------+-------------------+----------------+
"""
import os
from multiprocessing import Pool

import numpy as np
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams
from pdfminer.layout import LTTextBox
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import PDFObjRef, resolve1
from spellchecker import SpellChecker

import plix.helpers.common_functions as cf
import plix.helpers.table_utils as tau
import plix.helpers.text_utils as teu
import plix.nlp_assets as nlp_assets

spellcheck = SpellChecker()


def process_texts(dataframe, config):
    """
    handles the extraction of text from the pdfs.
    After the raw text is extracted, it is cleaned in a postprocessing step.
    Afterwards OCR is run if needed.
    If both methods were used, the more meaningful text is chosen.

    :param pd.DataFrame dataframe: dataframe object in which the data is saved.
    :param plix.config.Config config: pipeline config object

    :returns: dataframe object with added new data
    :rtype: pd.DataFrame
    """
    dataframe['Text'] = ''
    dataframe['cleanText'] = ''
    dataframe['OCRedText'] = ''
    dataframe['cleanOCRText'] = ''
    dataframe['MeaningfulText'] = ''
    dataframe['allText'] = ''

    if os.name == "nt":
        pytesseract.pytesseract.tesseract_cmd = config.tesseract_path

    if config.do_text_extraction:
        dataframe['Text'] = dataframe.apply(lambda x: __read_pdf_text(x['FullPath']), axis=1)
        dataframe['cleanText'] = dataframe['Text'].apply(lambda a: __clean_text(a, config.is_paperdata))

    if config.do_ocr or config.force_ocr:
        dataframe['OCRedText'] = dataframe.apply(
            lambda x: __parse_ocr(x['FullPath'], x['Text'], config.dtd_max_page_num,
                                  config.ocr_min_page_threshold, config.force_ocr),
            axis=1)
        dataframe['cleanOCRText'] = dataframe['OCRedText'].apply(lambda a: __clean_text(a, config.is_paperdata))

    if config.do_text_extraction or config.do_ocr:
        dataframe['MeaningfulText'] = dataframe.apply(lambda x: __choose_meaningful_text(x['cleanText'],
                                                                                         x['cleanOCRText'],
                                                                                         config.vocab_file,
                                                                                         config.ocr_min_page_threshold),
                                                      axis=1)
        dataframe['allText'] = dataframe['MeaningfulText'].apply(lambda page: ' '.join([str(v) for v in page.values()]))

    return dataframe


def process_metadata(dataframe):
    """
    Handles the extraction of metadata from the pdfs.

    :param pd.DataFrame dataframe: dataframe object in which the data is saved.

    :returns: dataframe object with added new data
    :rtype: pd.DataFrame
    """
    dataframe['Metadata'] = dataframe.apply(lambda x: __read_metadata(x['FullPath']), axis=1)
    dataframe['Filename'] = cf.get_filename(dataframe['FullPath'])
    dataframe['Category'] = get_category(dataframe['FullPath'])
    return dataframe


def process_tables(dataframe, tokenizer, coordinates, config):
    """
    Handles the extraction of tables from the pdfs.
    After the raw extraction, the tables get filtered to remove possible non-tables and a clean-up post-pressing is run.

    :param pd.DataFrame dataframe: dataframe object in which the data is saved.
    :param plix.tokenizer.Tokenizer tokenizer: tokenizer object
    :param pd.DataFrame coordinates: dataframe object of the coordinates of found tables
    :param plix.config.Config config: pipeline config object

    :returns: dataframe object with added new data
    :rtype: pd.DataFrame
    """
    dataframe['TableData'] = ''

    if os.name == "nt":
        pytesseract.pytesseract.tesseract_cmd = config.tesseract_path

    if config.do_table:
        dataframe['TableData'] = dataframe.apply(lambda x: __process_table_data(x['FullPath'], tokenizer, coordinates,
                                                                                config), axis=1)
    return dataframe


def get_category(full_path):
    """
    gets the category of the pdf document.

    :param pd.Series full_path: path and name of the document

    :returns: category
    :rtype: str
    """
    return full_path.apply(lambda x: os.path.basename(x[:x.rfind(os.sep)]))


def extract_all_data_from_files(dataframe, tokenizer, coordinates, config):
    """
    This func arranges the result dataframe using the absolute file path as an index.
    It performs all raw data extraction steps (text, table, OCR).

    :param pd.DataFrame dataframe: dataframe of all pdf text
    :param plix.tokenizer.Tokenizer tokenizer: tokenizer object
    :param pd.DataFrame coordinates: extracted table coordinates
    :param plix.config.Config config: pipeline config object

    :returns dataframe: the result
    :rtype: pd.DataFrame
    """
    dataframe = process_texts(dataframe, config)
    dataframe = process_metadata(dataframe)
    dataframe = process_tables(dataframe, tokenizer, coordinates, config)
    dataframe = cf.reorder_columns(dataframe, ['Filename',
                                               'FullPath',
                                               'Category',
                                               'TableData',
                                               'Metadata',
                                               'allText',
                                               'cleanText',
                                               'MeaningfulText',
                                               'Text',
                                               'cleanOCRText',
                                               'OCRedText'
                                               ])
    return dataframe


def __read_pdf_text(filename):
    cf.log('Reading file: ' + filename)
    pages = {}

    try:
        with open(filename, mode='rb') as fp:
            number_pdf_pages = PDFPage.get_pages(fp)
            resource_manager = PDFResourceManager()
            laparams = LAParams(char_margin=40, all_texts=True)
            device = PDFPageAggregator(resource_manager, laparams=laparams)
            interpreter = PDFPageInterpreter(resource_manager, device)
            # read (only) text page by page
            for i, page in enumerate(number_pdf_pages):
                interpreter.process_page(page)
                layout = device.get_result()
                text_arr = [lobj.get_text().replace('\xa0', ' ')
                            for lobj in layout
                            if isinstance(lobj, LTTextBox)]
                pages[i] = '\n'.join(text_arr)
            pages['total pages'] = i + 1
            cf.log('Extracted ' + str(pages['total pages']) + ' pages')
    except Exception as ex:
        cf.log('Error Read PDF: ' + str(ex))

    return pages


def __resolve_metadata(obj):
    if isinstance(obj, PDFObjRef):
        return resolve1(obj)
    elif str(type(obj)) == "<class 'bytes'>":
        return obj.decode("utf-8", errors='ignore')
    else:
        return obj


def __read_metadata(filename):
    metadata = {}
    with open(filename, mode='rb') as fp:
        try:
            parser = PDFParser(fp)
            doc = PDFDocument(parser)
            raw_metadata = doc.info
            for dat in raw_metadata:
                # expect only one object in this array
                for key in dat.keys():
                    if isinstance(dat[key], list):
                        new_arr = []
                        arr = dat[key]  # ???
                        for el in arr:
                            new_arr.append(__resolve_metadata(el))
                        dat[key] = new_arr
                    else:
                        dat[key] = __resolve_metadata(dat[key])
                    metadata[key] = dat[key]
            # add source url and file size
            file_size = os.path.getsize(filename)
            metadata['FileSize'] = file_size
        except Exception as ex:
            cf.log('Error reading metadata ' + filename + str(ex))
    return metadata


def __clean_text(raw_text, is_paperdata):
    if 'total pages' in raw_text.keys():
        raw_text.pop('total pages')

    space_text = teu.remove_non_printable(raw_text)  # remove non printable characters
    # remove hyphens from word separation caused by new lines cy-\ncle -> cycle
    no_hyphen = teu.replace_without_space(nlp_assets.REGEX['line_hyphen'], space_text)
    if is_paperdata:
        no_square_citation = teu.replace_without_space(nlp_assets.REGEX['square_bracket_citation'], no_hyphen)
    else:
        no_square_citation = no_hyphen
    no_cid = teu.replace_without_space(nlp_assets.REGEX['cid'], no_square_citation)
    no_newline = teu.replace_with_space(nlp_assets.REGEX['newline'], no_cid)
    cleaned_text = teu.replace_with_space(nlp_assets.REGEX['multi_spaces'], no_newline)
    if is_paperdata:
        cleaned_text = teu.cut_end_of_text(cleaned_text)
    return cleaned_text


def __choose_meaningful_text(text, ocr_text, vocab_file, ocr_min_page_threshold):
    if os.path.exists(vocab_file):
        spellcheck.word_frequency.load_text_file(vocab_file)
    better_text = {}
    if 'total pages' in text.keys():
        text.pop('total pages')
    # first check if both texts have same no of pages

    len_text = len(text)
    len_ocr = len(ocr_text)
    if len_text != len_ocr:
        cf.log('Meaningful text choice: not the same number of pages')
        better_text = text if len_text > len_ocr else ocr_text
    # then check lengths of text
    else:
        # iterate over the pages
        for i, (p_text, p_ocr) in enumerate(zip(text.values(), ocr_text.values())):
            if not isinstance(p_text, str) or not isinstance(p_ocr, str):
                continue
            # check lengths
            if len(p_text) < ocr_min_page_threshold <= len(p_ocr):
                cf.log('Meaningful text choice: OCR has more text')
                better_text[i] = p_ocr
            elif len(p_ocr) < ocr_min_page_threshold <= len(p_text):
                cf.log('Meaningful text choice: text extraction has more text')
                better_text[i] = p_text
            else:
                cf.log('Meaningful text choice: Deciding via spellchecker')
                errors_text = spellcheck.unknown(p_text.split())
                errors_ocr = spellcheck.unknown(p_ocr.split())
                better_text[i] = p_ocr if len(errors_text) > len(errors_ocr) else p_text

    return better_text


def __parse_ocr(filename, pages, dtd_max_page_num, ocr_min_page_thresh, force_ocr):
    ocred_pages = {}
    try:
        page_count = dtd_max_page_num
        # exclude 'total pages'
        if isinstance(pages, dict):
            if 'total pages' in pages.keys():
                pages.pop('total pages')
                page_count = len(pages.keys())
            all_text_len = sum([len(x) for x in pages.values()])
            pages['total pages'] = page_count  # add back
            # for time performance, use ocr when necessary, or set in config
            if force_ocr or all_text_len <= page_count * ocr_min_page_thresh:
                cf.log('Running OCR parser for ' + filename)
                # an installation file is needed, download from
                # https://github.com/UB-Mannheim/tesseract/wiki
                # tesseract4 is not working, please download version5.0.0
                pages = convert_from_path(filename, dpi=600, thread_count=4)
                tesser_config = '--psm 1'  # use no oem mode or 3
                i = 0
                for page in pages:
                    if i >= dtd_max_page_num:
                        break
                    ocred_pages[i] = pytesseract.image_to_string(page, lang='eng', config=tesser_config)
                    i += 1
                ocred_pages['total pages'] = len(pages)
    except Exception as ex:
        cf.log('OCRParser Error: ' + str(ex))

    return ocred_pages


def __process_table_data(full_path, tokenizer, coordinates, config):
    """
    This func extracts and processes tables from pdf files.

    When coordinates are present, tables are only extracted in the corresponding area. For ocr, the image is cut to the
    coordinate boundaries, and OCR is performed on the cut image with pytesseract. Afterwards, the table is extracted
    with Camelot.
    After all tables are extracted, they are futher processed to correct possible extraction errors and make them more
    readable and processable. Additionally, the tables are filtered to exclude possible graphs that were mistakenly
    detected in the coordinate calculation.

    The table-clean-up steps are:
    At first, potentially wrongly extracted tables are filtered out if all cells are empty ('') or numpy.NaN
    (not a number). Sometimes, Camelot can also extract the table description as the first row, so if a column contains
    the string 'Table', it is omitted. Often, it can also happen that one row is read as two rows by Camelot.
    This can for example be caused by subscripts. Therefore, rows are merged in the next step. Two subjacent rows are
    merged only if, for every cell, the cell is empty in one row and not empty in the other. Then, the empty cells are
    filled with the content from the cell in the other row and the lower row is omitted. For example:

    +---------+------+--------+
    |   name  | size | colour |
    +=========+======+========+
    | foo bar |      | blue   |
    +---------+------+--------+
    |         | 1.5  |        |
    +---------+------+--------+

    is merged into:

    +---------+------+--------+
    |   name  | size | colour |
    +=========+======+========+
    | foo bar | 1.5  | blue   |
    +---------+------+--------+

    As a last step before the filtering, every string is cleaned up similiar to the :func:`clean_text()` procedure
    (see below). Known extraction errors and multiple whitespaces are replaced, linebreaks, (cid: number) artifacts,
    and non-printable characters are removed. Since it is possible that graphs are recognized as tables by the edge
    detection in the coordinate calculation, these then filtered.

    :param str full_path: string to pdf file
    :param Tokenizer tokenizer: tokenizer object
    :param pd.Dataframe coordinates: extracted table coordinates

    :returns: all extracted tables after filtering
    :rtype: list of lists
    """

    table_data = __extract_tables(full_path, coordinates, config.table_modes, config.table_line_scale,
                                  config.table_whitespace_thresh, config.image_folder, config.ocr_pdf_path,
                                  config.ocr_image_path)
    table_data, i = __format_tables(table_data)
    # filter tables for possible graphs or images
    if config.filter_table:
        filtered_tables = __filter_tables(table_data, tokenizer, config.table_filter_max_row_thresh,
                                          config.table_filter_spaces_thresh, config.table_filter_meaningful_thresh,
                                          config.table_filter_empty_thresh)
    else:
        filtered_tables = table_data
    no_filtered = len(table_data) - len(filtered_tables)
    if i == 0:
        cf.log('No table found.')
    else:
        cf.log("Extracted " + str(len(table_data)) + " table(s)")
    cf.log("Filtered " + str(no_filtered) + " table(s)")
    cf.log(str(len(filtered_tables)) + " table(s) after filtering")

    return filtered_tables


def __extract_tables(full_path, coordinates, table_modes, table_line_scale, table_whitespace_thresh, image_folder,
                     ocr_pdf_path, ocr_image_path):
    # get from paths, {lattice, stream, ocr, no_table}
    mode = cf.get_mode(full_path, table_modes)
    file = os.path.basename(full_path)
    tables = []
    try:
        cf.log('Get tables: ' + full_path)
        if mode == 'no_table':
            return tables
        if mode == 'lattice':
            tables += tau.extract_lattice_tables(full_path, table_line_scale, table_whitespace_thresh)
        else:
            # both stream and OCR need coordinates
            table_coords, org_size, pt_size = tau.format_coordinates(full_path, coordinates)
            for i, cds in enumerate(table_coords):
                new_coords = cds['box']
                if mode == 'stream':
                    tables += tau.extract_stream_tables(full_path, new_coords, org_size, pt_size, cds)
                elif mode == 'ocr':
                    tables += tau.extract_ocr_tables(file, cds, new_coords, i, image_folder, ocr_pdf_path,
                                                     ocr_image_path)
                else:
                    raise ValueError("Table Extraction: No or wrong extraction mode specified")
    except Exception as ex:
        cf.log('Error reading table:' + full_path + ' ' + str(ex))
    return tables


def __format_tables(tables):
    formatted_tables = []
    i = 0
    for table in tables:
        table = tau.format_table(table)
        if not table.empty:
            table.apply(lambda col: tau.format_entry(col))
            if not table.empty:
                formatted_tables.append(table)
                i += 1
    return formatted_tables, i


def __filter_tables(table_data, tokenizer, table_filter_max_row_thresh, table_filter_spaces_thresh,
                    table_filter_meaningful_thresh, table_filter_empty_thresh):
    filtered_tables = []
    for df_tab in table_data:
        filtered_tab = tau.filter_possible_non_table(df_tab, tokenizer, table_filter_max_row_thresh,
                                                     table_filter_spaces_thresh, table_filter_meaningful_thresh,
                                                     table_filter_empty_thresh)
        if filtered_tab:
            filtered_tables.append(filtered_tab)
    return filtered_tables


class PDFDataExtractor:
    def __init__(self, directory, tokenizer, cores_no=1, coordinates=None):
        self.paths = cf.find_pdf_file_paths_in_directories(directory)
        self.extraction_results = None
        self.tokenizer = tokenizer
        self.no_cores = cores_no
        self.table_coordinates = coordinates

    def extract_data_from_pdfs(self, func=None, df=None, config=None):
        """
        Main function to run the data extraction.

        It extracts the text and tables from PDF files in folders specified in the config.
        The output is the extracted text plus other relevant information stored as pandas dataframe.

        :param function func: optional function to be run, if none, `extract_all_data_from_files` is run
        :param pd.DataFrame df: optional dataframe object to use, if none new one is created
        :param plix.config.Config config: config object from pipeline

        :returns: dataframe with the data from the extraction
        :rtype: pd.DataFrame
        """
        if func is None:
            func = extract_all_data_from_files
        if df is None:
            self.extraction_results = pd.DataFrame(self.paths, columns=['FullPath'])
        else:
            self.extraction_results = df
        self.__adjust_cores_if_needed()
        self.__parallelize_data_extraction(func, config)
        return self.extraction_results

    def __adjust_cores_if_needed(self):
        if len(self.extraction_results["FullPath"]) < self.no_cores:
            self.no_cores = len(self.extraction_results["FullPath"])

    def __parallelize_data_extraction(self, func, config):
        df_split = np.array_split(self.extraction_results, self.no_cores)
        pool = Pool(self.no_cores)
        if func.__name__ == 'process_texts':
            inputs = [(df_in, config) for df_in in df_split]
            self.extraction_results = pd.concat(pool.starmap(func, inputs))
        else:
            inputs = [(part, self.tokenizer, self.table_coordinates, config) for part in df_split]
            results = pool.starmap(func, inputs)
            self.extraction_results = pd.concat(results)
        pool.close()
        pool.join()
