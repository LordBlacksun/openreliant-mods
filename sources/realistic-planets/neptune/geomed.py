"""Reads Voyager ISS GEOMED images: PDS3, with a VICAR header record, then 1000 by 1000 16-bit
integers that are I/F times the label's REFLECTANCE_SCALING_FACTOR."""
import re

import numpy as np


def label(path):
    text = open(path, encoding='latin-1').read()
    fields = {}
    for key, value in re.findall(r'^\s*([A-Z_^]+)\s*=\s*(.+?)\s*$', text, re.M):
        fields.setdefault(key, value.strip().strip('"'))
    return fields


def image(path_img, path_lbl):
    """The image as I/F, and its label's fields."""
    fields = label(path_lbl)
    record = int(fields['RECORD_BYTES'])
    lines, samples = int(fields['LINES']), int(fields['LINE_SAMPLES'])
    start = int(re.search(r'\(".*?",\s*(\d+)\)', fields['^IMAGE']).group(1)) - 1
    raw = np.fromfile(path_img, dtype='<i2', count=lines * samples, offset=start * record)
    scale = float(fields.get('REFLECTANCE_SCALING_FACTOR', '1').split()[0])
    return raw.reshape(lines, samples).astype(np.float64) * scale, fields
