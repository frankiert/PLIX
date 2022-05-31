"""
This is an example script to demonstrate how to use the individual steps of the PLIX pipeline.
You do not need to run everything every time, configure it as you need it for your data.

For details, please check out the official documentation.
"""
import json
import os

import plix


def get_domain_knowledge(domain_knowledge_filepath: str) -> dict:
    """
    load a prepared json, returning a dict with the bespoken structure
    """
    with open(domain_knowledge_filepath, "r", encoding="utf-8") as f:
        domain_knowledge = json.loads(f.read())
    return domain_knowledge


def domain_knowledge_to_keywords_and_units(domain_knowledge):
    """
    converts json to internal data structure
    """
    keywords = []
    units = {}
    for key, vals in domain_knowledge.items():
        keywords.append([k for k in [key.strip()] + vals["synonyms"]])
        units[key] = {
            "base_units": [k for k in vals["units"][:1] if len(k.strip()) > 0],
            "prefixed_units": [k for k in vals["units"] if len(k.strip()) > 0],
            "base_symbols": [k for k in [vals["main_symbol"]] if len(k.strip()) > 0],
            "prefixed_symbols": [k for k in vals["symbols"] if len(k.strip()) > 0]
        }
    return keywords, units


def main():
    # make sure all needed folders exist
    content_root = os.path.join(os.curdir, "data")
    config = plix.Config(datasheets_folder=os.path.join(content_root, "datasheets"),
                         output_folder=os.path.join(content_root, "output"),
                         vocab_file=os.path.join(content_root, "vocab.txt"),
                         tesseract_path=os.path.join("..", "libs", "Tesseract-OCR", "tesseract.exe"),
                         table_modes=["lattice", "ocr", "stream"],
                         save_intermediate_results=False,
                         debug_mode=True
                         )

    pdf_list = plix.find_pdf_file_paths_in_directories(config.datasheets_folder)
    domain_knowledge = get_domain_knowledge(os.path.join(".", "data", "motor_dk.json"))
    keyword_list, unit_dict = domain_knowledge_to_keywords_and_units(domain_knowledge)
    tokenizer = plix.Tokenizer(config.vocab_file)

    # 1. Coordinates
    coordinates = plix.extract_coordinates(pdf_list, config.image_folder, config.table_image_folder, config.table_modes,
                                           config.tesseract_path, method='opencv')

    # 2. data extraction from PDFs
    data_extractor = plix.PDFDataExtractor(config.datasheets_folder, tokenizer, coordinates=coordinates)
    extracted_data = data_extractor.extract_data_from_pdfs(config=config)  # reads text and tables
    # for individual steps run:
    # extracted_text = data_extractor.extract_data_from_pdfs(plix.process_texts, config)
    # extracted_tables = data_extractor.extract_data_from_pdfs(plix.process_tables, config)

    # 3. classification
    extracted_data = plix.classify_texts(extracted_data)

    # 4. normalization
    keyword_list = plix.normalize_keyword_dk(keyword_list)
    unit_dict = plix.normalize_unit_dk(unit_dict)
    extracted_data['NormalizedTableData'] = extracted_data['TableData'].apply(
        lambda x: plix.normalize_tables(x, keyword_list, True))
    extracted_data['NormalizedText'] = extracted_data['MeaningfulText'].apply(lambda x: plix.normalize_text_per_page(x))

    # 5. kvu text
    kvu_text_results = plix.extract_text_kvu(extracted_data, keyword_list, unit_dict, max_len_text=75)
    kvu_text_results = plix.kvu_list_to_df(kvu_text_results)

    # 6. kvu table
    kvu_table_results = plix.extract_table_kvu(extracted_data, keyword_list, unit_dict, do_pivot_search=True)
    kvu_table_results = plix.kvu_list_to_df(kvu_table_results)

    # 7. merge
    merged_kvu_results = plix.remove_text_table_duplicates(kvu_table_results, kvu_text_results)

    # 8. done
    print(merged_kvu_results[["FileName", "Key", "Value", "Unit"]])


if __name__ == "__main__":
    main()
