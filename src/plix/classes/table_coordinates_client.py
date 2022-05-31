"""
This file contains functionality to calculate the coordinates for the tables in all data.

The resulting file has the following format:

+-----------+-------------+------------------------------------------------+-------------------------------------------------------------+
|   index   |   FullPath  |                      size                      |                         tableCoords                         |
+===========+=============+================================================+=============================================================+
| row index | path to pdf | size of the pdf images [ width, height ] in px | list of dictionaries of page number and list of coordinates |
|           |             |                                                | Coordinates are [ x1,y1,x2, y2] in px (origin: top left)    |
+-----------+-------------+------------------------------------------------+-------------------------------------------------------------+
"""

import os

import PIL
import pandas as pd
import pytesseract
from pdf2image import convert_from_path

import plix.classes.table_coordinate_calculator as tcc
import plix.helpers.common_functions as cf

SPLIT_THRESHOLD = 40


def extract_coordinates(pdf_paths, image_folder, table_image_folder, table_modes, tesser_path, method='opencv',
                        is_debug=False):
    """
    This func contains the main functionality. It calls the coordinate calculation and then stores all important data
    in a dataframe.

    :param list pdf_paths: paths to all pdfs
    :param str image_folder: path to where the converted images are saved
    :param str table_image_folder: path to where the images of the found tables are saved
    :param list table_modes: list of table modes
    :param str tesser_path: path to Tesseract exe
    :param str method: one of the two methods
    :param bool is_debug: set debug parameter, will save the images of the detected tables if set to True
    """
    if os.name == "nt":
        pytesseract.pytesseract.tesseract_cmd = tesser_path

    df = pd.DataFrame(pdf_paths, columns=['FullPath'])
    if method.lower() == 'opencv':
        df['size'] = df['FullPath'].apply(lambda file: __calculate_size(file, image_folder, table_modes))
        coordinates = tcc.get_tables_boundary(image_folder, table_image_folder, is_debug)
        df['tableCoords'] = df['FullPath'].apply(lambda file: __find_coordinates(file, coordinates, table_modes))
    else:
        raise ValueError('No or wrong method specified. Please use opencv')
    return df


# ---------------
# Helper functions


def __get_filename(full_path):
    return os.path.basename(full_path)


def __get_short_name(name):
    return name.replace(' ', '')[:SPLIT_THRESHOLD].rstrip()


# ---------------
# Functionality

def __filter_boxes(boxes, box_type):
    filtered_boxes = []
    # loop over objects in boxes
    for box in boxes:
        file = box['file']
        for b in box['boxes']:
            # if type matches
            if b['class'] == box_type:
                f_box = {'page': int(file.split('-')[-1].split('.')[0]), 'box': b['box']}
                # add to box_type
                filtered_boxes.append(f_box)
    cf.log("Table Extraction: Found " + str(len(filtered_boxes)) + " " + box_type + " coordinates")
    return filtered_boxes


def __calculate_size(file, target_folder, table_modes):
    # call opencv
    # if no images in config opencv input -> make input
    name = __get_filename(file)
    file_folder = os.path.join(target_folder, __get_short_name(name))

    table_cat = cf.get_mode(file, table_modes)
    if table_cat not in ['no_table', 'lattice']:
        # make one folder per document
        if not os.path.exists(file_folder):
            os.mkdir(file_folder)
        im_paths = os.listdir(file_folder)
        if not im_paths:
            # if no images have been converted yet
            cf.log("Coordinate Extraction: " + name + " No images found. Converting pdf to images...")
            _ = convert_from_path(file, dpi=300, output_folder=file_folder,
                                  output_file=table_cat + "_" + name[:SPLIT_THRESHOLD] + "-300-", fmt='png',
                                  grayscale=True, thread_count=4)  # pdf2image
            im_paths = os.listdir(file_folder)

        return list(PIL.Image.open(os.path.join(file_folder, im_paths[0])).size)
    else:
        return []


def __find_coordinates(file, coordinates, table_modes):
    name = __get_filename(file)
    table_coords = []
    if 'no_table' in file or 'lattice' in file:
        return table_coords

    cf.log("Getting the coordinates for " + name)
    short_name = name[:SPLIT_THRESHOLD]
    table_cat = cf.get_mode(file, table_modes)
    for key, value in coordinates.items():
        if key.startswith(table_cat + '_' + short_name):
            # get page number
            page = int(key.split('-')[-1].split('.')[0])
            for box in value:
                # value = list of lists of coordinates
                table_coord = {'page': page, 'box': box}
                table_coords.append(table_coord)
    cf.log("Table Extraction: Found " + str(len(table_coords)) + " coordinates")
    return table_coords
