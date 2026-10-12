"""Downloads what Saturn's textures are made from into a folder of its own: Cassini's global maps of
Saturn of 11 August 2011 in its red, green and blue filters, from the PDS Atmospheres Node; Hubble's
calibrated OPAL maps of Saturn of August 2025, both rotations, and of June 2018, at 395, 502 and 631
nm, from MAST; Karkoschka's 1993 albedo spectra of the giant planets, from the PDS Atmospheres Node;
Voyager 2's profiles of the rings, the delta Scorpii occultation and the lit side's brightness, from
the PDS Ring-Moon Systems Node; Cassini's natural colour mosaic across the rings (PIA11142), from
NASA's Photojournal; and the calibrated Cassini frames of Saturn's limb that the haze's listing
names, from the PDS Ring-Moon Systems Node.

    python3 fetch.py haze.json data
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import download  # noqa: E402

MAPS = 'https://atmos.nmsu.edu/PDS/data/PDS4/co_iss_global-maps/data_derived/Cassini_ISS_{}_Saturn_global_map.fits'
OPAL = 'https://archive.stsci.edu/hlsps/opal/{}/saturn/hlsp_opal_hst_wfc3-uvis_saturn-{}_{}_v1_globalmap.fits'
ROTATIONS = {'2025a': 'cycle32', '2025b': 'cycle32', '2018a': 'cycle25'}
VOYAGER = 'https://pds-rings.seti.org/holdings/volumes/VG_28xx/'
RINGS = [VOYAGER + 'VG_2801/EASYDATA/KM010/PS1P01.' + kind for kind in ('TAB', 'LBL')] + \
        [VOYAGER + 'VG_2810/DATA/IS2_P0001_V01_KM010.' + kind for kind in ('TAB', 'LBL')]
CASSINI = 'https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia11/pia11142/PIA11142.tif'

download.fetch([MAPS.format(f) for f in ('RED', 'GRN', 'BL1')] + [OPAL.format(cycle, rotation, f) for rotation, cycle in ROTATIONS.items() for f in ('f395n', 'f502n', 'f631n')]
               + download.KARKOSCHKA + RINGS + [CASSINI] + download.listed(sys.argv[1:-1]), sys.argv[-1])
