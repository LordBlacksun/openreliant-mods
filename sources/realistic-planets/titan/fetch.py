"""Downloads what Titan's texture and its haze are made from into a folder of its own: the calibrated
Cassini frames that the listings name, from the PDS Ring-Moon Systems Node, Cassini's map of Titan's
surface at 938 nm (PIA22770), from NASA's Photojournal, and Karkoschka's 1993 albedo spectra, from
the PDS Atmospheres Node.

    python3 fetch.py frames.json haze.json data
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import download  # noqa: E402

SURFACE = 'https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia22/pia22770/PIA22770.tif'

listings, out = sys.argv[1:-1], sys.argv[-1]
download.fetch(download.listed(listings) + [SURFACE] + download.KARKOSCHKA, out)
