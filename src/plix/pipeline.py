#!/usr/bin/env python3
"""
This class is for running PLIX' whole workflow.
Before you run it for the first time, please check the settings in the :class:`config` file.
"""
import datetime
import functools
import os
import shutil
import sys
from itertools import chain

import pandas as pd

import plix.classes.normalizer as nm
import plix.classes.pdf_data_extractor as pde
import plix.classes.table_coordinates_client as tcc
import plix.classes.table_info_extractor as taie
import plix.classes.text_classifier as tc
import plix.classes.text_info_extractor as teie
import plix.helpers.common_functions as cf
import plix.nlp_assets as nlp_assets
from plix.classes.tokenizer import Tokenizer


def timer(func):
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        cf.log("STARTED {}".format(func.__name__))
        then = datetime.datetime.now()
        value = func(*args, **kwargs)
        now = datetime.datetime.now()
        run_time = now - then
        cf.log("FINISHED {} in {}".format(func.__name__, run_time))
        return value

    return wrapper_timer


def _split_unit(unit):
    new_units = [unit]
    if '/' in unit:
        for w in unit.split('/'):
            new_units.append(w.strip())
    return new_units


def _create_keywords_list(units, keywords):
    keywords = set()
    if units:
        for entry, entry_dict in units.items():
            for new_unit in _split_unit(entry):
                keywords.add(new_unit)
            for unit_symbol, unit_symbol_list in entry_dict.items():
                for new_unit in _split_unit(unit_symbol):  # separate 'fraction units', e.g. kw/h
                    keywords.add(new_unit)
                for unit in unit_symbol_list:
                    for new_unit in _split_unit(unit):
                        keywords.add(new_unit)
    if keywords:
        for synonym_set in set(list(chain.from_iterable(keywords))):
            for word in synonym_set.split():
                keywords.add(word)
    return keywords


class Pipeline(object):

    def __init__(self, config):
        """
        The Pipeline class is used for defining the run of the PLIX pipeline as set in `config`.
        The needed resources are saved as class attributes.
        """
        self.config = config
        self.extraction_results = None
        self.kvu_text_results = None
        self.kvu_table_results = None
        self.merged_kvu_results = None
        self.keywords = None
        self.units = None
        self.tokenizer = None
        self.data_extractor = None
        cf.init_logging(logfile=self.config.log_file, do_print=self.config.debug_mode)

    ####################################################################################################################
    # HELPER METHODS                                                                                                   #
    ####################################################################################################################
    def __prepare_directories(self):
        if not os.path.exists(self.config.output_folder):
            os.mkdir(self.config.output_folder)
        if not os.path.exists(self.config.image_folder):
            os.mkdir(self.config.image_folder)
        if not os.path.exists(self.config.ocr_pdf_path):
            os.mkdir(self.config.ocr_pdf_path)
        if not os.path.exists(self.config.ocr_image_path):
            os.mkdir(self.config.ocr_image_path)
        if not os.path.exists(self.config.table_image_folder):
            os.mkdir(self.config.table_image_folder)

    def __remove_intermediate_directories(self):
        if self.config.datasheets_folder != self.config.image_folder:
            shutil.rmtree(self.config.image_folder, ignore_errors=True)
        if self.config.datasheets_folder != self.config.ocr_pdf_path:
            shutil.rmtree(self.config.ocr_pdf_path, ignore_errors=True)
        if self.config.datasheets_folder != self.config.ocr_image_path:
            shutil.rmtree(self.config.ocr_image_path, ignore_errors=True)
        if self.config.datasheets_folder != self.config.table_image_folder:
            shutil.rmtree(self.config.table_image_folder, ignore_errors=True)
        if self.config.datasheets_folder != self.config.output_folder:
            shutil.rmtree(self.config.output_folder, ignore_errors=True)

    def __prep_keys_and_units(self, key_value_retrieval_dict):
        self.keywords = []
        self.units = {}
        for key, vals in key_value_retrieval_dict.items():
            self.keywords.append([k for k in [key.strip()] + vals['synonyms']])
            self.units[key] = {
                'base_units': [k for k in vals['units'][:1] if len(k.strip()) > 0],
                'prefixed_units': [k for k in vals['units'] if len(k.strip()) > 0],
                'base_symbols': [k for k in [vals['main_symbol']] if len(k.strip()) > 0],
                'prefixed_symbols': [k for k in vals['symbols'] if len(k.strip()) > 0]
            }
        if self.config.do_normalization:
            self.keywords = nm.normalize_keyword_dk(self.keywords)
            self.units = nm.normalize_unit_dk(self.units)

    def __load_tokenizer(self, force_refresh=False):
        tokenizer = Tokenizer(self.config.vocab_file)
        # generate vocab if not done yet, empty vocab file yields length of 1
        if tokenizer.get_vocab_len() < 2 or force_refresh:
            keys_and_units = _create_keywords_list(self.units, self.keywords)
            to_be_added = set.union(keys_and_units, set(nlp_assets.DOMAIN_WORDS))
            tokenizer.generate_vocab(to_be_added)
            tokenizer.refresh_vocab()
        return tokenizer

    def __load_pdf_data_extractor(self):
        return pde.PDFDataExtractor(self.config.datasheets_folder, self.tokenizer, self.config.dataframe_cores)

    @timer
    def __preload_assets(self):
        try:
            if not self.config.is_new_data:
                self.extraction_results = cf.load_df(self.config.dataframe_file)
                # 11 is the column length after DE.read_files_to_dataframe
                assert len(self.extraction_results.columns) >= 11
            if self.config.do_table and not self.config.do_new_coordinates:
                self.data_extractor.table_coordinates = cf.load_df(self.config.coordinate_file)
            if self.config.do_merge and not self.config.is_new_data and not self.config.do_text_info_extraction:
                self.kvu_text_results = cf.load_df(self.config.text_info_file)
            if self.config.do_merge and not self.config.is_new_data and not self.config.do_table_info_extraction:
                self.kvu_table_results = cf.load_df(self.config.table_info_file)
        except FileNotFoundError as e:
            cf.log("Error preloading assets: " + str(e))
            sys.exit(1)

    ####################################################################################################################
    # PIPELINE STEPS                                                                                                   #
    ####################################################################################################################

    @timer
    def extract_coordinates(self):
        """
        This will generate table coordinates for files in the stream and ocr category.
        Please see :class:`classes.table_coordinates_client` for more information.
        """
        pdf_paths = self.data_extractor.paths
        coordinate_results = tcc.extract_coordinates(pdf_paths, self.config.image_folder,
                                                     self.config.table_image_folder,
                                                     self.config.table_modes, self.config.tesseract_path,
                                                     method='opencv', is_debug=self.config.debug_mode)
        self.data_extractor.table_coordinates = coordinate_results
        if self.config.save_intermediate_results:
            cf.save_df(self.data_extractor.table_coordinates, self.config.coordinate_file)

    @timer
    def prepare_dataset(self):
        """
        This executes the data set preparation and data extraction. This needs to be run, when new data sheets are used
        or steps in the extraction need to be repeated.

        For more information, please see :class:`classes.pdf_data_extractor` and
        :class:`classes.text_classifier`.
        """
        extraction_results = self.data_extractor.extract_data_from_pdfs(config=self.config)
        self.extraction_results = extraction_results
        # save data frame
        if self.config.save_intermediate_results:
            cf.save_df(self.extraction_results, self.config.result_file)

    @timer
    def extract_text(self):
        """
        This step extracts the test if and only if config.is_new_data` is false and
        `config.do_text_info_extraction` is set.
        """
        extraction_results = self.data_extractor.extract_data_from_pdfs(pde.process_texts, self.extraction_results,
                                                                        config=self.config)
        self.extraction_results = extraction_results
        if self.config.save_intermediate_results:
            cf.save_df(self.extraction_results, self.config.result_file)

    @timer
    def extract_tables(self):
        """
        This step extracts the test if and only if `config.is_new_data` is false and
        `config.do_table_info_extraction` is set.
        """
        extraction_results = self.data_extractor.extract_data_from_pdfs(pde.process_tables, self.extraction_results,
                                                                        config=self.config)
        self.extraction_results = extraction_results
        if self.config.save_intermediate_results:
            cf.save_df(self.extraction_results, self.config.result_file)

    @timer
    def classify_text(self):
        """
        Classifies the texts of all documents with the given classes.
        """
        classes_, counts = tc.classify_texts(self.extraction_results)
        self.extraction_results.loc[:, 'Classification'] = classes_
        self.extraction_results.loc[:, 'ClassificationCount'] = counts
        if self.config.save_intermediate_results:
            cf.save_df(self.extraction_results, self.config.result_file)

    @timer
    def normalize(self):
        """
        Normalization step. Formats text/tables/domain knowledge into a predefined format for easier KVU extraction
        """
        # table normalizer
        if cf.df_has_column(self.extraction_results, "TableData"):
            self.extraction_results.loc[:, 'NormalizedTableData'] = nm.normalize_tables_from_pd_series(
                self.extraction_results['TableData'], self.keywords, self.config.do_table_multiple_normalization)

        # text normalizer
        if cf.df_has_column(self.extraction_results, "MeaningfulText"):
            self.extraction_results.loc[:, 'NormalizedText'] = nm.normalize_text_from_pd_series(
                self.extraction_results['MeaningfulText'])

        if self.config.save_intermediate_results:
            cf.save_df(self.extraction_results, self.config.result_file)

    @timer
    def extract_text_information(self):
        """
        Extract KVU tuples from the running text.
        """
        kvu_text_results = teie.extract_text_kvu(self.extraction_results, self.keywords, self.units,
                                                 self.config.pdf_max_len_text)
        self.kvu_text_results = cf.kvu_list_to_df(kvu_text_results)
        if self.config.save_intermediate_results:
            cf.save_df(self.kvu_text_results, self.config.text_info_file)

    @timer
    def extract_table_information(self):
        """
        Extracts key-value-unit tuples of all tables.
        """
        kvu_table_results = taie.extract_table_kvu(self.extraction_results, self.keywords, self.units,
                                                   do_pivot_search=self.config.do_pivot_search)
        self.kvu_table_results = cf.kvu_list_to_df(kvu_table_results)
        if self.config.save_intermediate_results:
            cf.save_df(self.kvu_table_results, self.config.table_info_file)

    @timer
    def merge_info_extraction(self):
        """
        This func merges the results from the text and table key-value extraction.
        The result is saved in a new file.
        """
        self.merged_kvu_results = taie.remove_text_table_duplicates(self.kvu_table_results, self.kvu_text_results)
        cf.log("Entries after merging: " + str(len(self.merged_kvu_results.index)))
        if self.config.save_intermediate_results:
            cf.save_df(self.merged_kvu_results, self.config.merged_info_file, target=['csv', 'xlsx'])

    def run_pipeline(self, key_value_retrieval_dict):
        """
        This will start the execution of the pipeline. All steps set in `config` will be executed.
        """
        self.__prepare_directories()
        self.__prep_keys_and_units(key_value_retrieval_dict)
        self.tokenizer = self.__load_tokenizer(self.config.force_vocab_reload)
        self.data_extractor = self.__load_pdf_data_extractor()
        # load all needed data
        self.__preload_assets()

        if self.config.do_new_coordinates:
            self.extract_coordinates()
        if self.config.is_new_data:
            # run parallelization
            self.prepare_dataset()
        else:
            if self.config.do_text_extraction:
                self.extract_text()
            if self.config.do_table:
                self.extract_tables()
        if self.config.do_text_class:
            self.classify_text()
        if self.config.do_normalization:
            self.normalize()
        if self.config.do_text_info_extraction:
            self.extract_text_information()
        if self.config.do_table_info_extraction:
            self.extract_table_information()
        if self.config.do_merge or (self.config.do_text_info_extraction and self.config.do_table_info_extraction):
            self.merge_info_extraction()

        if not self.config.save_intermediate_results:
            self.__remove_intermediate_directories()
