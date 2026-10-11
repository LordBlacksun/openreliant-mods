"""Downloads what Neptune's texture is made from into a folder of its own: each frame's GEOMED image
and label that frames.json lists, from the PDS Ring-Moon Systems Node, and Karkoschka's 1993 albedo
spectra of the giant planets, from the PDS Atmospheres Node.

    python3 fetch.py frames.json data
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import download  # noqa: E402

listing, out = sys.argv[1], sys.argv[2]
urls = [u for frame in json.load(open(listing))['frames'] for u in frame['urls']]
download.fetch(urls + download.KARKOSCHKA, out)
