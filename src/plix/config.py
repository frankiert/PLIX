"""
Class for PLIX' configuration.
"""
import os


class Config:

    def __init_data_defaults(self, datasheets_folder, **kwargs):
        ############################
        # OUTPUT FOLDERS AND FILES #
        ############################
        self.output_folder = kwargs.get('output_folder', os.path.join(datasheets_folder, os.pardir, 'output'))
        self.dataframe_file = kwargs.get('dataframe_file', os.path.join(self.output_folder, 'extracted_pdf_data'))
        self.coordinate_file = kwargs.get('coordinate_file', os.path.join(self.output_folder, 'coordinates_opencv'))
        self.table_info_file = kwargs.get('table_info_file', os.path.join(self.output_folder, 'table_kvu'))
        self.text_info_file = kwargs.get('text_info_file', os.path.join(self.output_folder, 'kvu_text_filtered'))
        self.merged_info_file = kwargs.get('merged_info_file', os.path.join(self.output_folder, 'kvu_merged'))

        self.image_folder = kwargs.get('image_folder', os.path.join(self.output_folder, 'images_fullsize'))
        self.table_image_folder = kwargs.get('table_image_folder', os.path.join(self.output_folder,
                                                                                'opencv_images_filtered'))
        self.ocr_pdf_path = kwargs.get('ocr_pdf_path', os.path.join(self.output_folder, 'ocr_pdfs'))
        self.ocr_image_path = kwargs.get('ocr_image_path', os.path.join(self.output_folder, 'ocr_tables'))
        self.result_file = kwargs.get('result_file', os.path.join(self.output_folder, 'extracted_pdf_data'))

    def __init_table_extraction_config(self, **kwargs):
        ########################################
        # TABLE EXTRACTION CONFIGURATION       #
        ########################################
        self.table_modes = kwargs.get('table_modes', ['lattice', 'ocr', 'stream', 'no_table'])
        self.table_line_scale = kwargs.get('table_line_scale', 40)
        self.table_whitespace_thresh = kwargs.get('table_whitespace_thresh', 50)
        self.table_filter_empty_thresh = kwargs.get('table_filter_empty_thresh', 0.56)
        self.table_filter_meaningful_thresh = kwargs.get('table_filter_meaningful_thresh', 0.4)
        self.table_filter_spaces_thresh = kwargs.get('table_filter_spaces_thresh', 0.6)
        self.table_filter_max_row_thresh = kwargs.get('table_filter_max_row_thresh', 56)

    def __init_pipeline_configuration(self, **kwargs):
        ########################################
        # PIPELINE STEPS CONFIGURATION         #
        ########################################
        # Toggle this variable when you want to reread PDF files
        self.is_new_data = kwargs.get('is_new_data', True)
        # do post-processing for scientific papers
        self.is_paperdata = kwargs.get('is_paperdata', True)
        self.is_satellite_data = kwargs.get('is_satellite_data', False)
        # run the coordinate extraction
        self.do_new_coordinates = kwargs.get('do_new_coordinates', True)
        # extract text from pdf
        self.do_text_extraction = kwargs.get('do_text_extraction', True)
        # run OCR if necessary
        self.do_ocr = kwargs.get('do_ocr', True)
        # force to run OCR even when not necessary
        self.force_ocr = kwargs.get('force_ocr', False)
        # run table extraction
        self.do_table = kwargs.get('do_table', True)
        # filter the tables if graphs could have been read
        self.filter_table = kwargs.get('filter_table', True)
        # do text classification needs list of classes
        self.do_text_class = kwargs.get('do_text_class', True)
        # run text normalization on text, table, domain knowledge
        self.do_normalization = kwargs.get('do_normalization', True)
        # during the normalization, split up tables with multiple keywords in a cell
        self.do_table_multiple_normalization = kwargs.get('do_table_multiple_normalization', True)
        # run text-based information extraction
        self.do_text_info_extraction = kwargs.get('do_text_info_extraction', True)
        # run information extraction on tables
        self.do_table_info_extraction = kwargs.get('do_table_info_extraction', True)
        # enable pivot search  pattern for kvu table extraction
        self.do_pivot_search = kwargs.get('do_pivot_search', False)
        # merge text and table key-value pairs after extraction
        self.do_merge = kwargs.get('do_merge', True)

    def __init__(self, datasheets_folder, **kwargs):
        self.datasheets_folder = datasheets_folder
        self.__init_data_defaults(datasheets_folder, **kwargs)
        self.__init_pipeline_configuration(**kwargs)
        self.__init_table_extraction_config(**kwargs)

        # others
        self.tesseract_path = kwargs.get("tesseract_path", os.path.join("..", "..", "libs", "Tesseract-OCR",
                                                                        "tesseract.exe"))
        self.save_intermediate_results = kwargs.get('save_intermediate_results', True)

        self.vocab_file = kwargs.get('vocab_file', None)
        self.force_vocab_reload = kwargs.get('force_vocab_reload', False)
        # if less words, run ocr
        self.ocr_min_page_threshold = kwargs.get('ocr_min_page_threshold', 600)
        self.dataframe_cores = kwargs.get('dataframe_cores', 2)
        self.dtd_max_page_num = kwargs.get('dtd_max_page_num', 50)
        self.pdf_max_len_text = kwargs.get('pdf_max_len_text', 100)
        self.log_file = kwargs.get('log_file', os.path.join(self.output_folder, os.pardir, 'log.txt'))
        self.debug_mode = kwargs.get('debug_mode', False)
