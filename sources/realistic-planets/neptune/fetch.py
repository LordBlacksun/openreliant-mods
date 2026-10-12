"""Downloads what Neptune's texture and its haze are made from into a folder of its own: each frame's
GEOMED image and label that the listings name, from the PDS Ring-Moon Systems Node, and Karkoschka's
1993 albedo spectra of the giant planets, from the PDS Atmospheres Node.

    python3 fetch.py frames.json haze.json data
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import download  # noqa: E402

listings, out = sys.argv[1:-1], sys.argv[-1]
download.fetch(download.listed(listings) + download.KARKOSCHKA, out)
