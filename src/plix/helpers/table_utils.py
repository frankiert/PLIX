"""
This file provides table processing methods to help with the data extraction.
"""
import os
import random
import re
from string import printable

import camelot
import cv2
import ftfy
import numpy as np
import pandas as pd
import pytesseract
from pattern.text.en import singularize

import plix.helpers.common_functions as cf
import plix.nlp_assets as nlp_assets


####################################################################################################################
# PUBLIC EXTRACTION METHODS                                                                                        #
####################################################################################################################


def extract_lattice_tables(full_path, table_line_scale, table_whitespace_thresh):
    """
    Method to extract lattice tables.

    :param str full_path: path to pdf
    :param float table_line_scale: line_scale parameter for Camelot
    :param float table_whitespace_thresh: threshold for Camelot whitespace parameter

    :returns: extracted tables
    :rtype: pd.DataFrame
    """
    tables = []
    cf.log("Table Extraction: Lattice mode")

    tables_lat = camelot.read_pdf(full_path, pages='all', flavor='lattice', line_scale=table_line_scale)
    for d in tables_lat:
        if not d.df.empty and d.whitespace <= table_whitespace_thresh:
            tables.append(d.df)
    return tables


def extract_stream_tables(full_path, new_coords, org_size, pt_size, cds):
    """
    Method to extract stream tables.

    :param str full_path: path to pdf
    :param list new_coords: coordinates of the table bounding box
    :param list org_size: size of page image in px
    :param list pt_size: size of page image in pt
    :param dict cds: coordinates dict from file

    :returns: extracted tables
    :rtype: pd.DataFrame
    """
    tables = []
    cf.log("Table Extraction: Stream mode")
    conv_coords = __transform_from_to(new_coords, org_size, pt_size)  # px -> pt
    # sort to fit for camelot, transform y coordinates to fit origin in bottom left
    conv_coords = __sort_camelot_coordinates(conv_coords, pt_size[1])
    conv_coords = ','.join([str(x) for x in conv_coords])  # camelot needs coordinates as a comma-separated string
    try:
        tables_str = camelot.read_pdf(full_path, pages=str(cds['page']), table_areas=[conv_coords], flavor='stream',
                                      edge_tol=500)
        for d in tables_str:
            if not d.df.empty:
                tables.append(d.df)
    except Exception as ex:
        cf.log("Table Extraction: Camelot error, pdf has no text or no table. Error message: " + str(ex))
    return tables


def extract_ocr_tables(file, cds, new_coords, i, image_folder, ocr_pdf_path, ocr_image_path):
    """
    Method to extract ocr tables.

    :param str file: name of the pdf
    :param pd.DataFrame cds: coordinates object
    :param dict cds: coordinates dict from file
    :param list new_coords: coordinates of the table bounding box
    :param int i: current page number
    :param str image_folder: folder where the images of the pdf pages are
    :param str ocr_pdf_path: path where to store the generated table pdfs
    :param str ocr_image_path: path where the table images are

    :returns: extracted tables
    :rtype: pd.DataFrame
    """
    tables = []
    cf.log("Table Extraction: OCR mode")
    image_folder = os.path.join(image_folder, file.replace(' ', '')[:40].rstrip())
    pdf_file = os.path.join(ocr_pdf_path, ('table_' + file.replace(' ', '')[:40].rstrip() + str(cds['page']) + '_' +
                                           str(i) + '.pdf'))
    if not os.path.exists(ocr_pdf_path):
        os.mkdir(ocr_pdf_path)
    if not os.path.isfile(pdf_file):  # if none have been generated before
        __generate_pdf_from_ocr(file, image_folder, pdf_file, cds, new_coords, ocr_image_path)
    # table extraction from table pdfs
    try:
        tables_cam = camelot.read_pdf(pdf_file, flavor='stream', edge_tol=500)
        for d in tables_cam:
            tables.append(d.df)
    except Exception as ex:
        cf.log("Table Extraction: Camelot error, pdf has no text or no table. Error message: " + str(ex))
    return tables


####################################################################################################################
# TABLE IMAGE-RELATED METHODS                                                                                      #
####################################################################################################################


def format_coordinates(full_path, coordinates):
    """
    Gets coordinates from the coordinates object for the pdf file and converts them.

    :param str full_path: path to the current PDF file
    :param pd.DataFrame coordinates: the coordinates object

    :returns: the converted coordinates, the size of the image in px, the size of the image in pt
    :rtype: tuple
    """
    row = coordinates[coordinates.FullPath.isin([full_path])]  # get correct row
    row = row.reset_index(drop=True)
    table_coords = row['tableCoords'][0]  # get only the table coordinates
    org_size = row['size'][0]  # original size of the picture of the page
    pt_size = __calculate_pt_size(org_size)  # get pt size
    return table_coords, org_size, pt_size


def __calculate_pt_size(size):
    # size = size in px e.g. (2550 x 3301 px)
    # returns size in pt e.g. (612 x 792.24 pt)
    # IMPORTANT: formula is for 300dpi images only
    return [x * 6 / 25 for x in size]


def __transform_from_to(coords, size_from, size_to):
    # Coordinate transformation from one interval to another
    for i, c in enumerate(coords):
        if i % 2 == 0:
            coords[i] = round(c / size_from[0] * size_to[0])
        else:
            coords[i] = round(c / size_from[1] * size_to[1])
    return coords


def __sort_camelot_coordinates(coords, y_size):
    transformed = [0] * 4
    transformed[0] = coords[0]  # x1
    transformed[1] = abs(coords[1] - y_size)  # y1 coordinate transformation origin upper left -> lower left
    transformed[2] = coords[2]  # x2
    transformed[3] = abs(coords[3] - y_size)  # y2
    return transformed


def __get_image_path_from_page_no(images_path, page):
    im_file = ''
    images = os.listdir(images_path)
    for image in images:
        if image.endswith('.png'):
            if int(image.split('-')[-1].split('.')[0]) == page:
                im_file = os.path.join(images_path, image)
    return im_file


def __remove_lines(image):
    def remove_lines_one_direction(img, kernel_size):
        # binarize image with threshold
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        # https://stackoverflow.com/a/58089157
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)  # define kernel
        # morphological opening (erosion followed by dilation) removes noise
        remove = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)
        # find contours (lines) and draw them over
        cnts = cv2.findContours(remove, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            cv2.drawContours(img, [c], -1, (255, 255, 255), 15)
        return img

    removed = image.copy()
    # grayscaled image
    gray = cv2.cvtColor(removed, cv2.COLOR_BGR2GRAY)
    # Remove vertical lines
    removed_vertical = remove_lines_one_direction(gray, (1, 40))
    # Remove horizontal lines
    removed_horizontal = remove_lines_one_direction(removed_vertical, (40, 1))
    return removed_horizontal


def __generate_pdf_from_ocr(file, image_folder, pdf_file, cds, new_coords, ocr_image_path):
    prepared_image = __prepare_ocr_image(file, image_folder, cds, new_coords, ocr_image_path)
    # table image + OCR'ed text to pdf
    pdf = pytesseract.image_to_pdf_or_hocr(prepared_image, extension='pdf', config='--psm 4')
    with open(pdf_file, 'w+b') as f:
        f.write(pdf)  # pdf type is bytes by default


def __prepare_ocr_image(file, image_folder, cds, new_coords, ocr_image_path):
    # generate name for image, since they are all stored in the same directory, add random number to prevent
    # overwriting of an image
    image_file = os.path.join(ocr_image_path, ('table_' + file.replace(' ', '')[:40].rstrip() + str(cds['page']) + '_' +
                                               str(random.randrange(1, 1000000)) + '.png'))
    cf.log("Table Extraction: Generating OCR pdfs...")
    img_p = __get_image_path_from_page_no(image_folder, cds['page'])
    img = cv2.imread(img_p)
    crop_img = img[new_coords[1]:new_coords[3], new_coords[0]:new_coords[2]]  # crop to table
    no_line_img = __remove_lines(crop_img)
    if not os.path.exists(ocr_image_path):
        os.mkdir(ocr_image_path)
    cv2.imwrite(image_file, no_line_img)  # save image for later reuse
    return no_line_img


####################################################################################################################
# TABLE MANIPULATION METHODS                                                                                       #
####################################################################################################################


def format_table(table):
    """
    Applies several formatting functions to a table.

    :param pd.DataFrame table: the table

    :returns: the formatted table
    :rtype: pd.DataFrame
    """
    table = table.replace(r'^\s*$', np.NaN, regex=True)  # multiple whitespaces
    table.apply(lambda col: __remove_description_row(col))
    table = table.dropna('columns', 'all')  # remove all NaN columns
    table = table.dropna('index', 'all')
    table = table.reset_index(drop=True)
    table = __merge_xor_rows(table)
    table = table.reset_index(drop=True)
    return table


def format_entry(col):
    """
    Formats each cell in a column.

    :param pd.Series col: column
    """
    for i, entry in enumerate(col):
        str_entry = str(entry)
        if str_entry.lower() == 'nan':
            col[i] = ' '
        else:
            str_entry = ftfy.fix_text(str_entry)  # remove known extraction errors
            str_entry = str_entry.replace('\n', ' ')  # for lattice mode with line-spanning entries
            str_entry = re.sub(" +", ' ', str_entry)  # multiple whitespaces to only one
            str_entry = re.sub(nlp_assets.REGEX['cid'], '', str_entry)  # remove (cid: no)
            col[i] = ''.join(filter(lambda x: x in printable, str_entry))  # remove non-printables


def filter_possible_non_table(df_tab, tokenizer, table_filter_max_row_thresh, table_filter_spaces_thresh,
                              table_filter_meaningful_thresh, table_filter_empty_thresh):
    """
     Potential graphs are excluded if:

    - they have more than 56% empty cells or
    - 40% of the cells do not include meaningful strings (correct English words or numbers) or
    - they have less than 2 columns and 5 rows or
    - they include a certain keyword (Algorithm number: , doi:, etc.)
    - they have more than 56 rows
    - less than 60% of the entries only have one word (this filters potential legends and scales)

    :param pd.DataFrame df_tab: dataframe containing the tables
    :param plix.classes.tokenizer.Tokenizer tokenizer: the tokenizer object
    :param float table_filter_max_row_thresh: threshold how many rows a table should have max
    :param float table_filter_spaces_thresh: threshold how many cells with spaces a table should have max
    :param float table_filter_meaningful_thresh: threshold how many cells with meaningful text a table should have min
    :param float table_filter_empty_thresh: threshold how many empty cells a table should have max
    """
    if len(df_tab.index) > table_filter_max_row_thresh:
        return
    elif len(df_tab.columns) == 1 and len(df_tab[df_tab[df_tab.columns[0]].str.len() != 0].index) > 0:
        col = df_tab[df_tab.columns[0]]
        split_col = [len(str(x).split(' ')) > 1 for x in col]
        if sum(split_col) < round(len(col) * table_filter_spaces_thresh):
            return
    sum_cells = 0
    sum_count = 0
    for col in df_tab.columns.values:
        # count number of cells with meaningful text or numbers
        (k, count) = __find_meaningful_cells(df_tab[col], tokenizer)
        sum_cells += k
        sum_count += count
    if sum_cells < round(sum_count * table_filter_meaningful_thresh):
        # is filtered out
        return
    else:
        cells = df_tab.size
        df_tab = df_tab.replace(r'^\s*$', np.NaN, regex=True)
        nans = df_tab.isna().sum().sum()
        number_of_rows = len(df_tab.index)
        number_of_columns = len(df_tab.columns)
        df_tab = df_tab.replace(np.NaN, ' ', regex=True)
        # filter if contains specific words or regexes
        if df_tab.apply(lambda col: __should_filter(col), axis=0).any():
            # is filtered out
            return
        # if there are not more NaN cells than the threshold
        elif nans < round(cells * table_filter_empty_thresh):
            if number_of_columns >= 2 or number_of_rows >= 5:  # if table is not too small
                return df_tab.values.tolist()  # found a table
            else:
                # is filtered out
                return
        else:
            # is filtered out
            return


def __merge_xor_rows(df):
    """
    Often, it can also happen that one row is read as two rows by Camelot. This can for example be
    caused by subscripts. Therefore, rows are merged in the next step. Two subjacent rows are merged only if, for every
    cell, the cell is empty in one row and not empty in the other (like an xor). Then, the empty cells are filled with
    the content from the cell in the other row and the lower row is omitted. For example:

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
    """
    done = False
    while not done:
        row_list = df.values.tolist()
        done = True
        for i in range(len(row_list) - 1):
            current_row = row_list[i]
            next_row = row_list[i + 1]
            x = pd.isnull(current_row)
            y = pd.isnull(next_row)
            match = [a != b for a, b in zip(x, y)]
            if all(match):
                # if one cell is empty in one row, but not empty in the other
                df_temp = pd.DataFrame([current_row, next_row], index=[0, 0])
                # merge rows
                df_temp = df_temp.head(1).combine_first(df_temp.tail(1))
                # save merged row
                df.loc[i] = df_temp.values.tolist()[0]
                # remove now obsolete row
                df = df.drop(axis=1, index=(i + 1))
                done = False
    return df


def __remove_description_row(col):
    for i, entry in enumerate(col):
        str_entry = str(entry)
        if str_entry.lower().startswith('table'):
            col[i] = np.NaN


def __should_filter(col):
    for entry in col:
        str_entry = str(entry)
        for w in nlp_assets.TABLE_FILTER:
            if re.search(r'\b({}:)'.format(w), str_entry):
                return True
    return False


def __find_meaningful_cells(col, tokenizer):
    j = 0
    len_col = 0
    for entry in col:
        str_entry = str(entry)
        str_list = str_entry.split(' ')  # split into words
        len_col += len(str_list)
        for word in str_list:
            singular_word = singularize(re.sub(r'[^a-zA-Z]', '', word.lower()))
            # cell is either a number or an English word
            if re.match(nlp_assets.REGEX['number'],
                        re.sub(r'\W', '', word, 1)) or tokenizer.is_token_in_vocab(singular_word):
                j += 1
    return j, len_col
