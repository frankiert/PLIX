"""
Example file how to run PLIX in the command line.
"""
import json
import os

from plix import Config, Pipeline


def get_domain_knowledge(domain_knowledge_filepath: str) -> dict:
    """
    load a prepared json, returning a dict with the bespoken structure
    """
    with open(domain_knowledge_filepath, "r", encoding="utf-8") as f:
        domain_knowledge = json.loads(f.read())
    return domain_knowledge


def main():
    content_root = os.path.join(os.curdir, "data")
    # set config for pipeline as needed
    config = Config(
        datasheets_folder=os.path.join(content_root, "datasheets"),
        output_folder=os.path.join(content_root, "output"),
        vocab_file=os.path.join(content_root, "vocab.txt"),
        log_file=os.path.join(content_root, 'plix.log'),
        tesseract_path=os.path.join("..", "libs", "Tesseract-OCR", "tesseract.exe"),
        is_new_data=True,
        do_new_coordinates=True,
        do_text_extraction=True,
        do_ocr=True,
        force_ocr=False,
        do_table=True,
        do_normalization=True,
        do_text_class=False,
        do_text_info_extraction=True,
        do_table_info_extraction=False,
        do_merge=True,
        force_vocab_reload=False,
        save_intermediate_results=True,
        pdf_max_len_text=75,
        dataframe_cores=1,
        debug_mode=True
    )

    domain_knowledge = get_domain_knowledge(os.path.join(".", "data", "motor_dk.json"))
    plix_pl = Pipeline(config)
    # run pipeline with domain knowledge
    plix_pl.run_pipeline(domain_knowledge)


if __name__ == "__main__":
    main()
