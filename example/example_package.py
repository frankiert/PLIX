"""
Example file how to use PLIX in your own code as a package.
"""
import json
import os

from plix import Config, Pipeline


def get_domain_knowledge_from_file(domain_knowledge_filepath: str) -> dict:
    """
    load a prepared json, returning a dict with the bespoken structure
    """
    with open(domain_knowledge_filepath, "r", encoding="utf-8") as f:
        domain_knowledge = json.loads(f.read())
    return domain_knowledge


def get_config(ds_folder, vocab_file):
    """
    returns a simple pipeline configuration
    """
    return Config(
        datasheets_folder=ds_folder,
        vocab_file=vocab_file,
        tesseract_path=os.path.join("..", "libs", "Tesseract-OCR", "tesseract.exe"),
        do_text_class=False,
        do_normalization=True,
        save_intermediate_results=False,
    )


def process_file(ds_folder, vocab_file, domain_knowledge):
    """
    small function to run the pipeline and return the extraction results.
    """
    config = get_config(ds_folder, vocab_file)
    ppl = Pipeline(config)
    ppl.run_pipeline(domain_knowledge)
    return {
        "extraction": ppl.extraction_results,
        "kvu_text": ppl.kvu_text_results,
        "kvu_table": ppl.kvu_table_results,
        "merged_kvu": ppl.merged_kvu_results,
    }


if __name__ == "__main__":
    content_root = os.path.join(os.curdir, "data")

    ds_folder = os.path.join(content_root, "datasheets")
    vocab_file = os.path.join(content_root, "vocab.txt")
    domain_knowledge = get_domain_knowledge_from_file(os.path.join(".", "data", "motor_dk.json"))

    results = process_file(ds_folder, vocab_file, domain_knowledge)

    print(results["kvu_text"])
    print(results["merged_kvu"])
