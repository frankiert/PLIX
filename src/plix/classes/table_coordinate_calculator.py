"""
Detects tables and calculates their bounding boxes.
"""
import os
import pathlib

import cv2
import pytesseract

import plix.helpers.common_functions as cf


def get_tables_boundary(image_folder, table_image_folder, is_debug):
    """
    Detects tables in images of pdf pages.

    :param str image_folder: path to folder of converted pages to image
    :param str table_image_folder: folder where debug images are saved
    :param bool is_debug: if this is set, images with the bounding boxes of the tables are saved

    :returns: all detected table coordinates
    :rtype: dict
    """
    detected_table = {}
    files = __get_files_in_directory(image_folder, extension='.png')
    if not files:
        cf.log("Table Coordinate Calculator: Error no image files found, returning..")
        return detected_table
    # read each image file
    for image_file in files:
        img = cv2.imread(str(image_file))
        if img is None:
            cf.log("Table Coordinate Calculator: Error loading image {}, returning..".format(image_file))
            return detected_table

        boxes = DetectTable(img).run()
        # ignore small boxes or nested boxes (relative to the page size)
        selected_boxes = _select_boxes(boxes, min_height=1, min_width=1)
        # read each box >> crop to small images
        # and check if the cropped image contains (readable) text
        ind = 0
        detected_table_count = 0
        coordinates = []
        # coordinate is [x1,y1,x2,y2] originates in top left corner
        for b in selected_boxes:
            # select the area from y1:y2, x1:x2
            crop_img = img.copy()[b[1]:b[3], b[0]:b[2]]
            # ocr for text in the cropped area
            text_rows, text_boxes, text_img_ratio = _detect_text(crop_img)
            # consider only a box with text more than one row
            # and if the image contains at least 20% of text
            # draw rectangles over the image (x1,y1), (x2,y2)
            coordinates.append(b)
            if is_debug:
                cv2.rectangle(img, (b[0], b[1]), (b[2], b[3]), (0, 0, 255), 4)
                # draw rectanles over the cropped image
                for tb in text_boxes:
                    cv2.rectangle(crop_img, (tb[0], tb[1]), (tb[2], tb[3]), (255, 0, 255), 2)
            detected_table_count += 1
            ind += 1
        # save a page with boxes only if a table is detected
        if detected_table_count > 0:
            filename = os.path.basename(image_file)
            if is_debug:
                cv2.imwrite(str(pathlib.PurePath(table_image_folder, filename)), img)
            detected_table[filename] = coordinates
    return detected_table


def _select_boxes(boxes, min_height=0, min_width=0):
    # select only if the width and height are enough
    selected_boxes = []
    for [x1, y1, x2, y2] in boxes:
        if ((y2 - y1) >= min_height) & (x2 - x1 >= min_width) & ([x1, y1, x2, y2] not in selected_boxes):
            selected_boxes.append([x1, y1, x2, y2])

    return selected_boxes


def _detect_text(img):
    text = pytesseract.image_to_string(img, lang='eng', config='--psm 12 --oem 3')
    boxes = pytesseract.image_to_boxes(img)
    img_h = img.shape[0]
    img_w = img.shape[1]
    row_boxes = boxes.split('\n')
    row_boxes = [row.split(' ') for row in row_boxes
                 if len(row.strip()) > 0]
    # the y1 and y2 start in bottom left, so we need to flip & swap them
    boxes = [[int(b[1]), img_h - int(b[4]), int(b[3]), img_h - int(b[2])] for b in row_boxes]
    boxes = [[b[0], b[1], b[2], b[3]] for b in boxes if (b[2] - b[0] < 0.8 * img_w) & (b[3] - b[1] < 0.8 * img_h)]
    # must merge again, these are textbox from tesseract
    txt_img_ratio = _get_text_areas(boxes) / (img_h * img_w)
    rows = text.split('\n')
    text_rows = [row for row in rows if len(row.strip()) > 0]
    return text_rows, boxes, txt_img_ratio


def _get_h_lines(h_img):
    h_size = int(h_img.shape[1] * 0.05)
    h_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (h_size, 1))
    h_erode_img = cv2.erode(h_img, h_structure, 1)
    h_dilate_img = cv2.dilate(h_erode_img, h_structure, iterations=1)
    return h_dilate_img


def _get_v_lines(v_img):
    v_size = int(v_img.shape[0] * 0.05)
    v_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_size))
    v_erode_img = cv2.erode(v_img, v_structure, 1)
    v_dilate_img = cv2.dilate(v_erode_img, v_structure, iterations=1)
    return v_dilate_img


def _add_vertical_lines(table_lines, h_margin=4):
    # if there are non-connected single lines,
    # which are equal in size and vertically aligned,
    # draw vertical lines to connect them
    connect_lines = []
    for [a_x1, a_y1, a_x2, a_y2] in table_lines:
        for [b_x1, b_y1, b_x2, b_y2] in table_lines:
            is_same_line = (a_x1 == b_x1) & (a_y1 == b_y1) & \
                           (a_x2 == b_x2) & (a_y2 == b_y2)
            if is_same_line:
                break
            is_v_align = (abs(a_x1 - b_x1) <= h_margin) & (abs(a_x2 - b_x2) <= h_margin)

            if is_v_align:
                # draw vertical lines
                y1 = min(a_y1, b_y1)
                y2 = max(a_y2, b_y2)
                connect_lines.append([a_x1, y1, a_x2, y2])
    return connect_lines


def _select_box_with_line(boxes, table_lines):
    table_boxes = []
    for box in boxes:
        [box_x1, box_y1, box_x2, box_y2] = box
        for table_line in table_lines:
            [table_x1, table_y1, table_x2, table_y2] = table_line

            has_table_line = (table_x1 >= box_x1) & (table_x2 <= box_x2) & \
                             (table_y1 >= box_y1) & (table_y2 <= box_y2)
            is_long_line_ = ((table_x2 - table_x1) >= 0.5 * (box_x2 - box_x1))

            if has_table_line & is_long_line_:
                table_boxes.append(box)
    return table_boxes


def _remove_footer_header(boxes, max_height):
    no_header_boxes = []
    for box in boxes:
        [x1, y1, x2, y2] = box
        if not (((y1 <= 0.1 * max_height) | (y2 >= 0.9 * max_height)) &
                (y2 - y1 <= 0.05 * max_height)):
            no_header_boxes.append(box)
    return no_header_boxes


def _get_text_areas(boxes):
    area = 0
    for [x1, y1, x2, y2] in boxes:
        w = x2 - x1
        h = y2 - y1
        area += w * h
    return area


def __get_files_in_directory(folder_path, extension):
    file_list = []
    for path, subdirs, files in os.walk(folder_path):
        for name in files:
            if name.lower().endswith(extension):
                file_list.append(pathlib.PurePath(path, name))
    return file_list


class DetectTable:
    def __init__(self, src_img):
        self.src_img = src_img
        self.img_height = src_img.shape[0]
        self.img_width = src_img.shape[1]

    def run(self):
        """
        starts the table detection.
        """
        gray_img = []
        if len(self.src_img.shape) == 2:
            gray_img = self.src_img
        elif len(self.src_img.shape) == 3:
            gray_img = cv2.cvtColor(self.src_img, cv2.COLOR_BGR2GRAY)

        thresh_img = cv2.adaptiveThreshold(~gray_img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)

        # look for vertical and horizontal lines
        h_img = _get_h_lines(thresh_img)
        v_img = _get_v_lines(thresh_img)

        mask_line_img = h_img + v_img
        line_contours, line_hierarchy = cv2.findContours(mask_line_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        table_lines = self.__group_contours(line_contours)

        connect_lines = _add_vertical_lines(table_lines)
        for b in connect_lines:
            cv2.rectangle(thresh_img, (b[0], b[1]), (b[2], b[3]), (255, 255, 255), 2)

        structure = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                              (int(self.img_width * 0.01), int(self.img_height * 0.01)))
        text_dilate_img = cv2.dilate(thresh_img.copy(), structure, anchor=(-1, -1), iterations=1)
        text_contours, text_hierarchy = cv2.findContours(text_dilate_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # get bounding boxes around any text
        boxes = self.__group_contours(text_contours)

        # repeat until no more box can be merged
        old_box_count = len(boxes) + 1
        ind = 0
        while old_box_count > len(boxes):
            old_box_count = len(boxes)
            grouped_boxes = self.__group_overlapped_boxes(boxes, table_lines, h_margin=10, v_margin=4)
            merged_boxes = self.__group_nested_boxes(grouped_boxes, table_lines)
            cluster_boxes = self.__group_neighbours(merged_boxes, table_lines, h_margin=10, v_margin=4)
            boxes = cluster_boxes
            ind += 1

        # assume that a table contains at least one line
        table_boxes = _select_box_with_line(boxes, table_lines)

        return table_boxes

    def __group_contours(self, contours):
        rectangles = []
        # scan all contours and add to rectangles group
        for contour in contours:
            point_x, point_y = [], []
            for [[x, y]] in contour:
                point_x.append(x)
                point_y.append(y)
            x1 = min(point_x)
            x2 = max(point_x)
            y1 = min(point_y)
            y2 = max(point_y)
            rectangles.append([x1, y1, x2, y2])

        no_header_boxes = _remove_footer_header(rectangles, self.img_height)
        # sort by y1 value
        sorted_boxes = sorted(no_header_boxes, key=lambda x: x[1])
        return sorted_boxes

    def __group_overlapped_boxes(self, rectangles, table_lines, h_margin=0, v_margin=0):
        # group rectangles that are vertically and horizontally overlapped
        boxes = []
        for [a_x1, a_y1, a_x2, a_y2] in rectangles:
            i = 0
            part_found = False

            # compare with the output boxes
            for [b_x1, b_y1, b_x2, b_y2] in boxes:

                #       a_x1,a_y1--------------------------a_x1,b_y1 
                # b_x1,b_y1 |                     b_x2,b_y1|
                #   |------------------------------|       |
                #   |       |                      |       |
                is_a_right_to_b = ((a_x1 >= b_x1) & (a_x1 - h_margin <= b_x2)) | \
                                  ((b_x2 + h_margin >= a_x1) & (b_x2 <= a_x2))

                # a_x1,a_y1                       a_x2,a_y1
                #   |------------------------------|
                #   |   b_x1,b_y1------------------|-------b_x1,b_y1 
                #   |       |                      |       | 
                is_a_left_to_b = ((a_x2 + h_margin >= b_x1) & (a_x2 <= b_x2)) | \
                                 ((b_x1 >= a_x1) & (b_x1 - h_margin <= a_x2))

                is_h_overlapped = is_a_right_to_b | is_a_left_to_b

                # b_x1,b_y1----------------------b_x2,b_y1
                #   |                              |
                #   |   a_x1,a_y1------------------|-----a_x1,b_y1 
                #   |       |                      |       | 
                # b_x1,b_y2-|--------------------b_x2,b_y2 |
                #           |                              |
                #       a_x1,a_y2------------------------a_x2,a_y2 
                is_a_under_b = ((a_y1 >= b_y1) & (a_y1 - v_margin <= b_y2)) | \
                               ((b_y2 + v_margin >= a_y1) & (b_y2 <= a_y2))
                #       a_x1,a_y1----------------------a_x2,a_y1
                #           |                              |
                # b_x1,b_y1-|-------------------b_x1,b_y1  | 
                #   |       |                      |       |
                #   |   a_x1,a_y2------------------|-----a_x2,a_y2  
                #   |                              | 
                # b_x1,b_y2- --------------------b_x2,b_y2  
                is_a_above_b = ((a_y2 + v_margin >= b_y1) & (a_y2 <= b_y2)) | \
                               ((b_y1 >= a_y1) & (b_y1 - v_margin <= a_y2))
                is_v_overlapped = is_a_under_b | is_a_above_b

                # print(is_h_overlapped,is_v_overlapped)
                # join 2 boxes if they overlap or are overlapped
                if is_h_overlapped & is_v_overlapped:
                    x1 = min([a_x1, b_x1])
                    x2 = max([a_x2, b_x2])
                    y1 = min([a_y1, b_y1])
                    y2 = max([a_y2, b_y2])

                    # join if the new box is smaller than one fifth of page
                    new_box = (x2 - x1) * (y2 - y1)
                    is_new_box_too_big = new_box >= 0.2 * (self.img_width * self.img_height)
                    if is_new_box_too_big:
                        break

                    # if the lower box contains table lines, skip it
                    is_lower_box_table = False
                    o_x1, o_y1, o_x2, o_y2 = a_x1, a_y1, a_x2, a_y2
                    if is_a_above_b:
                        o_x1, o_y1, o_x2, o_y2 = b_x1, b_y1, b_x2, b_y2
                    for [l_x1, l_y1, l_x2, l_y2] in table_lines:

                        if (l_x1 >= o_x1) & (l_y1 >= o_y1) & (l_x2 <= o_x2) & (l_y2 <= o_y2):
                            is_lower_box_table = True
                            break
                    if is_lower_box_table:
                        break

                    boxes[i] = [x1, y1, x2, y2]
                    part_found = True

                i += 1
            if not part_found:
                boxes.append([a_x1, a_y1, a_x2, a_y2])
        return boxes

    def __group_nested_boxes(self, boxes, table_lines):
        merged_boxes = []
        for [x1, y1, x2, y2] in boxes:
            # select only if the box is not inside another box
            ind_s = 0
            found_nested_box = False
            for [o_x1, o_y1, o_x2, o_y2] in merged_boxes:
                # if the current box is a superset of another box
                # x1,y1
                #   |-------------------------------------------|
                #   |   o_x1,o_y1--------------------------|    |              
                #   |       |                              |    |
                #   |       |--------------------------o_x2,o_y2|
                #   |-----------------------------------------x2,y2
                #                                                    
                # choose the bigger box
                if (o_x1 >= x1) & (o_x2 <= x2) & (o_y1 >= y1) & (o_y2 <= y2):

                    # merge if the bigger box is smaller than one fifth of page
                    new_box = (x2 - x1) * (y2 - y1)
                    is_new_box_too_big = new_box >= 0.2 * (self.img_width * self.img_height)
                    if is_new_box_too_big:
                        break

                    # if the smaller box contains table lines, skip it
                    is_small_box_table = False
                    for [l_x1, l_y1, l_x2, l_y2] in table_lines:
                        if (l_x1 >= o_x1) & (l_y1 >= o_y1) & (l_x2 <= o_x2) & (l_y2 <= o_y2):
                            is_small_box_table = True
                            break
                    if is_small_box_table:
                        break

                    merged_boxes[ind_s] = [x1, y1, x2, y2]
                    found_nested_box = True
                    break
                # if the current box is a subset of another box, do nothing
                # o_x1,o_y1
                #   |-------------------------------------------|
                #   |     x1,y1----------------------------|    |              
                #   |       |                              |    |
                #   |       |----------------------------x2,y2  |
                #   |---------------------------------------o_x2,o_y2
                #                                                    
                elif (o_x1 <= x1) & (o_x2 >= x2) & (o_y1 <= y1) & (o_y2 >= y2):
                    found_nested_box = True
                    break
                ind_s += 1
                # if neither superset nor a subset of another box, then add it to the list
            if not found_nested_box:
                merged_boxes.append([x1, y1, x2, y2])
        return merged_boxes

    def __group_neighbours(self, boxes, table_lines, h_margin=0, v_margin=0):
        merged_boxes = []
        for [a_x1, a_y1, a_x2, a_y2] in boxes:
            # merge only if the box is next to another box
            ind_s = 0
            found_neighbour_box = False

            for [b_x1, b_y1, b_x2, b_y2] in merged_boxes:

                is_h_align = ((b_y1 <= a_y1) & (a_y1 <= b_y2)) | \
                             ((b_y1 <= a_y2) & (a_y2 <= b_y2))
                is_h_neighbor = ((abs(a_x2 - b_x1) <= h_margin) |
                                 (abs(a_x1 - b_x2) <= h_margin)) & is_h_align
                is_v_align = ((a_x1 <= b_x1) & (b_x1 <= a_x2)) | \
                             ((a_x1 <= b_x2) & (b_x2 <= a_x2))
                is_v_neighbor = ((abs(a_y2 - b_y1) <= v_margin) |
                                 (abs(a_y1 - b_y2) <= v_margin)) & is_v_align
                if is_h_neighbor | is_v_neighbor:
                    x1 = min([a_x1, b_x1])
                    x2 = max([a_x2, b_x2])
                    y1 = min([a_y1, b_y1])
                    y2 = max([a_y2, b_y2])

                    # join if the new box is smaller than one fifth of page
                    new_box = (x2 - x1) * (y2 - y1)
                    is_new_box_too_big = new_box >= 0.2 * (self.img_width * self.img_height)
                    if is_new_box_too_big:
                        break

                    # merge only if the box above is bigger than the one below
                    size_a = (a_x2 - a_x1) * (a_y2 - a_y1)
                    size_b = (b_x2 - b_x1) * (b_y2 - b_y1)
                    is_a_above_b = (a_y1 <= b_y1)
                    is_a_under_b = (a_y1 > b_y1)
                    is_upper_box_bigger = (is_a_above_b & (2 * size_a >= size_b)) | \
                                          (is_a_under_b & (size_a <= 2 * size_b))

                    # if the lower box contains table lines, skip it
                    is_lower_box_table = False
                    o_x1, o_y1, o_x2, o_y2 = a_x1, a_y1, a_x2, a_y2
                    if is_a_above_b:
                        o_x1, o_y1, o_x2, o_y2 = b_x1, b_y1, b_x2, b_y2
                    for [l_x1, l_y1, l_x2, l_y2] in table_lines:

                        if (l_x1 >= o_x1) & (l_y1 >= o_y1) & (l_x2 <= o_x2) & (l_y2 <= o_y2):
                            is_lower_box_table = True
                            break
                    if is_lower_box_table:
                        break

                    if is_h_neighbor | is_upper_box_bigger:
                        merged_boxes[ind_s] = [x1, y1, x2, y2]
                        break

                ind_s += 1
            # if neither superset nor a subset of an other box, then add it to the list
            if not found_neighbour_box:
                merged_boxes.append([a_x1, a_y1, a_x2, a_y2])
        return merged_boxes
