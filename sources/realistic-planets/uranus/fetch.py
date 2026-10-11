"""Downloads what Uranus's texture is made from into a folder of its own: Hubble's calibrated OPAL maps
of Uranus of November 2022 at 467, 547 and 657 nm, from MAST, and Karkoschka's 1993 albedo spectra of
the giant planets, from the PDS Atmospheres Node.

    python3 fetch.py data
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import download  # noqa: E402

OPAL = 'https://archive.stsci.edu/hlsps/opal/cycle30/uranus/hlsp_opal_hst_wfc3-uvis_uranus-2022a_{}_v1_globalmap.fits'

download.fetch([OPAL.format(f) for f in ('f467m', 'f547m', 'f657n')] + download.KARKOSCHKA, sys.argv[1])
