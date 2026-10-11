"""Reads the image of a FITS file, as Hubble's OPAL maps hold it: a header of 80-character cards in
blocks of 2880 bytes, ending at the card END, then a 2-dimensional array of 32-bit floats in
big-endian order, its rows in the order the file has them."""
import numpy as np

BLOCK = 2880
CARD = 80


def image(path):
    """The image at `path`, as an array of rows."""
    header = {}
    with open(path, 'rb') as f:
        ended = False
        while not ended:
            block = f.read(BLOCK)
            if len(block) < BLOCK:
                raise ValueError(f"{path}: the header ends without END")
            for at in range(0, BLOCK, CARD):
                card = block[at:at + CARD].decode('ascii')
                key = card[:8].strip()
                if key == 'END':
                    ended = True
                    break
                if card[8:10] == '= ':
                    header[key] = card[10:].split('/')[0].strip()
        if int(header['BITPIX']) != -32 or int(header['NAXIS']) != 2:
            raise ValueError(f"{path}: not a 2-dimensional image of 32-bit floats")
        width, height = int(header['NAXIS1']), int(header['NAXIS2'])
        data = np.fromfile(f, dtype='>f4', count=width * height)
    return data.reshape(height, width).astype(np.float64)
