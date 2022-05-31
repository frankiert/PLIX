"""
Miscellaneous functions that are used in several modules.
"""
import logging
import os
import sys
from glob import glob

import pandas as pd


def init_logging(logfile: str = 'logfile.log', do_print: bool = True) -> None:
    """
    Method to init the logging.

    :param str logfile: file where to save the logging
    :param bool do_print: if this is set, logging will be printed in console
    """
    logger = logging.getLogger('PLIX')
    logger.setLevel(logging.INFO)

    filehandle = logging.FileHandler(filename=logfile, encoding='utf-8', mode='a+')
    streamhandle = logging.StreamHandler(sys.stdout)

    format_ = logging.Formatter("%(asctime)s %(name)s :: %(levelname)s :: %(message)s", datefmt="%F %T")

    filehandle.setLevel(logging.INFO)
    streamhandle.setLevel(logging.INFO if do_print else logging.WARNING)

    filehandle.setFormatter(format_)
    streamhandle.setFormatter(format_)

    logger.addHandler(filehandle)
    logger.addHandler(streamhandle)


def log(message, level=logging.INFO):
    """
    Logs a message to the log file and optionally prints the message.

    :param str message: message that should be logged
    :param int level: logging level
    """
    logger = logging.getLogger('PLIX')
    if level == logging.INFO:
        logger.info(message)
    elif level == logging.WARNING:
        logger.warning(message)
    elif level == logging.error:
        logger.error(message)
    else:
        # logging.DEBUG
        logger.debug(message)


def is_folder_and_not_empty(path):
    """
    checks whether a given path is a not empty folder

    :param str path: the path to check

    :returns: true if conditions are met
    :rtype: bool
    """
    is_path_dir = os.path.isdir(path)
    is_not_empty = len(os.listdir(path)) > 0
    return is_path_dir and is_not_empty


def save_df(df: pd.DataFrame, fname: str, target=None):
    """
    Function to store df in up to three different formats
    (pickle serialization, csv, xlsx).

    :param pd.DataFrame df: dataframe object with intermediate results
    :param str fname: name for the file to be saved as
    :param list target: file extensions to save
    """
    if target is None:
        target = ['pkl', 'csv']
    if 'pkl' in target:
        df.to_pickle(fname + '.pkl')
    if 'csv' in target:
        df.to_csv(fname + '.csv')
    if 'xlsx' in target:
        df.to_excel(fname + '.xlsx')


def load_df(fname):
    """
    loads a .pkl from file to a dataframe.

    :returns: the dataframe
    :rtype: pd.DataFrame
    """
    return pd.read_pickle(fname + '.pkl')


def df_pkl_exists(fname):
    """
    Checks whether a pkl file exists.

    :param str fname: path to pkl file, minus the .pkl

    :returns: true if it exists
    :rtype: bool
    """
    return os.path.exists(fname + '.pkl')


def read_from_file(file_path):
    """
    Reads in a text file.

    :param str file_path: file path

    :returns: the file's contents
    :rtype: str
    """
    try:
        with open(file_path, mode='r', encoding='utf8') as file_:
            return file_.read()
    except OSError as err:
        log('Error while reading {}: {}'.format(file_path, str(err)))
    return ''


def get_filename(full_path):
    """
    Simple function to get only the file name from a complete path.

    :param pd.Series full_path:

    :returns: the base file name
    :rtype: pd.Series
    """
    return full_path.apply(os.path.basename)


def find_pdf_file_paths_in_directories(root_path):
    """
    Function to get all paths for the files.

    :param str root_path: root path of all pdf files

    :returns: list of paths for all pdf files
    :rtype: list
    """
    if not os.path.exists(root_path):
        raise OSError(f"The provided path does not exist: {root_path}")

    return [path for path in glob(os.path.join(root_path, '**', '*.[pP][dD][fF]'), recursive=True)
            if not os.path.isdir(path)]


def get_mode(full_path, table_modes):
    """
    gets the table extraction mode (lattice, stream, ocr, no_table).

    :param str full_path: path to pdf file
    :param list table_modes: the modes

    :returns: the mode
    :rtype: str
    """
    path_split = full_path.split(os.sep)
    mode = ''
    for m in table_modes:
        if m in path_split:
            mode = m
    return mode


def reorder_columns(dataframe, new_ordered_columns):
    """
    Function to reorder columns in a dataframe object.

    :param pd.DataFrame dataframe: dataframe object that needs to re rearranged
    :param list new_ordered_columns: list in which order the columns are to be arranged

    :returns: reordered dataframe object
    :rtype: pd.DataFrame
    """
    return dataframe[new_ordered_columns]


def kvu_list_to_df(results):
    """
    converts list of lists (of the KVU tuples) to a Pandas dataframe.

    :param list results: result list

    :returns: list as dataframe
    :rtype: pd.DataFrame
    """
    cols = ['FileName', 'Key', 'MatchedSynonym', 'Value', 'Unit', 'Surroundings', 'PageOrTableNumber', 'Classification']
    df = pd.DataFrame(results, columns=cols)
    return df


def df_has_column(df, column):
    """
    checks whether a pandas dataframe has a column.

    :param pd.Dataframe df: the series object to check
    :param str column: the column name to check

    :returns: true if it has the column
    :rtype: bool
    """
    return column in df.columns and (len(df[df[column].str.len() != 0].index) > 0)


def series_has_column(pd_series, column):
    """
    checks whether a pandas series has a column.

    :param pd.Series pd_series: the series object to check
    :param str column: the column name to check

    :returns: true if it has the column
    :rtype: bool
    """
    return column in pd_series.index and pd_series[column]
