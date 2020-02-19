import collections
import os
import shutil
import struct

import cv2
import numpy
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from . import ClientConstants as CC
from . import ClientImageHandling, ClientImporting, ClientParsing, ClientPaths
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusPaths, HydrusSerialisable
from . import QtPorting as QP

if cv2.__version__.startswith('2'):

    IMREAD_UNCHANGED = cv2.CV_LOAD_IMAGE_UNCHANGED

else:

    IMREAD_UNCHANGED = cv2.IMREAD_UNCHANGED


def CreateTopImage(width, title, payload_description, text):

    text_extent_qt_image = HG.client_controller.bitmap_manager.GetQtImage(
        20, 20, 24)

    painter = QG.QPainter(text_extent_qt_image)

    text_font = QW.QApplication.font()

    basic_font_size = text_font.pointSize()

    payload_description_font = QW.QApplication.font()

    payload_description_font.setPointSize(int(basic_font_size * 1.4))

    title_font = QW.QApplication.font()

    title_font.setPointSize(int(basic_font_size * 2.0))

    texts_to_draw = []

    current_y = 6

    for (t, f) in ((title, title_font), (payload_description,
                                         payload_description_font),
                   (text, text_font)):

        painter.setFont(f)

        wrapped_texts = WrapText(painter, t, width - 20)
        line_height = painter.fontMetrics().height()

        wrapped_texts_with_ys = []

        if len(wrapped_texts) > 0:

            current_y += 10

            for wrapped_text in wrapped_texts:

                wrapped_texts_with_ys.append((wrapped_text, current_y))

                current_y += line_height + 4

        texts_to_draw.append((wrapped_texts_with_ys, f))

    current_y += 6

    top_height = current_y

    del painter
    del text_extent_qt_image

    #

    top_qt_image = HG.client_controller.bitmap_manager.GetQtImage(
        width, top_height, 24)

    painter = QG.QPainter(top_qt_image)

    painter.setBackground(QG.QBrush(QC.Qt.white))

    painter.eraseRect(painter.viewport())

    #

    painter.drawPixmap(width - 16 - 5, 5, CC.GlobalPixmaps.file_repository)

    #

    for (wrapped_texts_with_ys, f) in texts_to_draw:

        painter.setFont(f)

        for (wrapped_text, y) in wrapped_texts_with_ys:

            (t_width,
             t_height) = painter.fontMetrics().size(QC.Qt.TextSingleLine,
                                                    wrapped_text).toTuple()

            QP.DrawText(painter, (width - t_width) // 2, y, wrapped_text)

    del painter

    data_bytearray = top_qt_image.bits()

    if QP.qtpy.PYSIDE2:

        data_bytes = bytes(data_bytearray)

    elif QP.qtpy.PYQT5:

        data_bytes = data_bytearray.asstring(top_height * width * 3)

    top_image_rgb = numpy.fromstring(data_bytes, dtype='uint8').reshape(
        (top_height, width, 3))

    top_image = cv2.cvtColor(top_image_rgb, cv2.COLOR_RGB2GRAY)

    top_height_header = struct.pack('!H', top_height)

    byte0 = top_height_header[0:1]
    byte1 = top_height_header[1:2]

    top_image[0][0] = ord(byte0)
    top_image[0][1] = ord(byte1)

    return top_image


def DumpToPng(width, payload_bytes, title, payload_description, text, path):

    payload_bytes_length = len(payload_bytes)

    header_and_payload_bytes_length = payload_bytes_length + 4

    payload_height = int(header_and_payload_bytes_length / width)

    if (header_and_payload_bytes_length / width) % 1.0 > 0:

        payload_height += 1

    top_image = CreateTopImage(width, title, payload_description, text)

    payload_length_header = struct.pack('!I', payload_bytes_length)

    num_empty_bytes = payload_height * width - header_and_payload_bytes_length

    header_and_payload_bytes = payload_length_header + payload_bytes + b'\x00' * num_empty_bytes

    payload_image = numpy.fromstring(header_and_payload_bytes,
                                     dtype='uint8').reshape(
                                         (payload_height, width))

    finished_image = numpy.concatenate((top_image, payload_image))

    # this is to deal with unicode paths, which cv2 can't handle
    (os_file_handle, temp_path) = HydrusPaths.GetTempPath(suffix='.png')

    try:

        cv2.imwrite(temp_path, finished_image,
                    [cv2.IMWRITE_PNG_COMPRESSION, 9])

        shutil.copy2(temp_path, path)

    except Exception as e:

        HydrusData.ShowException(e)

        raise Exception('Could not save the png!')

    finally:

        HydrusPaths.CleanUpTempPath(os_file_handle, temp_path)


def GetPayloadBytes(payload_obj):

    if isinstance(payload_obj, bytes):

        return payload_obj

    elif isinstance(payload_obj, str):

        return bytes(payload_obj, 'utf-8')

    else:

        return payload_obj.DumpToNetworkBytes()


def GetPayloadTypeString(payload_obj):

    if isinstance(payload_obj, bytes):

        return 'Bytes'

    elif isinstance(payload_obj, str):

        return 'String'

    elif isinstance(payload_obj, HydrusSerialisable.SerialisableList):

        type_string_counts = collections.Counter()

        for o in payload_obj:

            type_string_counts[GetPayloadTypeString(o)] += 1

        type_string = ', '.join(
            (HydrusData.ToHumanInt(count) + ' ' + s
             for (s, count) in list(type_string_counts.items())))

        return 'A list of ' + type_string

    elif isinstance(payload_obj, HydrusSerialisable.SerialisableBase):

        return payload_obj.SERIALISABLE_NAME

    else:

        return repr(type(payload_obj))


def GetPayloadDescriptionAndBytes(payload_obj):

    payload_bytes = GetPayloadBytes(payload_obj)

    payload_description = GetPayloadTypeString(
        payload_obj) + ' - ' + HydrusData.ToHumanBytes(len(payload_bytes))

    return (payload_description, payload_bytes)


def LoadFromPng(path):

    # this is to deal with unicode paths, which cv2 can't handle
    (os_file_handle, temp_path) = HydrusPaths.GetTempPath()

    try:

        shutil.copy2(path, temp_path)

        numpy_image = cv2.imread(temp_path, flags=IMREAD_UNCHANGED)

    except Exception as e:

        HydrusData.ShowException(e)

        raise Exception('That did not appear to be a valid image!')

    finally:

        HydrusPaths.CleanUpTempPath(os_file_handle, temp_path)

    try:

        try:

            (height, width) = numpy_image.shape

        except:

            raise Exception('The file did not appear to be monochrome!')

        try:

            complete_data = numpy_image.tostring()

            top_height_header = complete_data[:2]

            (top_height, ) = struct.unpack('!H', top_height_header)

            payload_and_header_bytes = complete_data[width * top_height:]

        except:

            raise Exception('Header bytes were invalid!')

        try:

            payload_length_header = payload_and_header_bytes[:4]

            (payload_bytes_length, ) = struct.unpack('!I',
                                                     payload_length_header)

            payload_bytes = payload_and_header_bytes[4:4 +
                                                     payload_bytes_length]

        except:

            raise Exception('Payload bytes were invalid!')

    except Exception as e:

        message = 'The image loaded, but it did not seem to be a hydrus serialised png! The error was: {}'.format(
            str(e))
        message += os.linesep * 2
        message += 'If you believe this is a legit non-resized, non-converted hydrus serialised png, please send it to hydrus_dev.'

        raise Exception(message)

    return payload_bytes


def TextExceedsWidth(painter, text, width):

    (t_width, t_height) = painter.fontMetrics().size(QC.Qt.TextSingleLine,
                                                     text).toTuple()

    return t_width > width


def WrapText(painter, text, width):

    words = text.split(' ')

    lines = []

    next_line = []

    for word in words:

        if word == '':

            continue

        potential_next_line = list(next_line)

        potential_next_line.append(word)

        if TextExceedsWidth(painter, ' '.join(potential_next_line), width):

            if len(potential_next_line) == 1:  # one very long word

                lines.append(' '.join(potential_next_line))

                next_line = []

            else:

                lines.append(' '.join(next_line))

                next_line = [word]

        else:

            next_line = potential_next_line

    if len(next_line) > 0:

        lines.append(' '.join(next_line))

    return lines
