"""Downloads what Jupiter's texture is made from into a folder of its own: Cassini's cylindrical map of
Jupiter of December 2000 (PIA07782), from NASA's Photojournal; Hubble's calibrated OPAL maps of January
2015 at 395, 502 and 631 nm, from MAST; and Karkoschka's 1993 albedo spectra of the giant planets, from
the PDS Atmospheres Node.

    python3 fetch.py data
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import download  # noqa: E402

CASSINI = 'https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia07/pia07782/PIA07782.tif'
OPAL = 'https://archive.stsci.edu/hlsps/opal/cycle22/jupiter/hlsp_opal_hst_wfc3-uvis_jupiter-2015a_{}_v1_globalmap.fits'

download.fetch([CASSINI] + [OPAL.format(f) for f in ('f395n', 'f502n', 'f631n')] + download.KARKOSCHKA, sys.argv[1])
