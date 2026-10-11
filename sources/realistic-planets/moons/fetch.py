"""Downloads what the textures of Jupiter's moons and Triton are made from into a folder of its own:
the Voyager frames that frames.json lists, from the PDS Ring-Moon Systems Node, and the global mosaic
of each moon, from the USGS's Astrogeology Science Center.

    python3 fetch.py frames.json data
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import download  # noqa: E402

MOSAICS = 'https://planetarymaps.usgs.gov/mosaic/'
MAPS = ['Io_Galileo_SSI_Global_Mosaic_1km.tif', 'Europa_Voyager_GalileoSSI_global_mosaic_500m.tif',
        'Ganymede_Voyager_GalileoSSI_global_mosaic_1km.tif', 'Callisto_Voyager_GalileoSSI_global_mosaic_1km.tif',
        'Triton_Voyager2_ClrMosaic_GlobalFill_600m.tif']

listing, out = sys.argv[1], sys.argv[2]
with open(listing) as f:
    urls = [url for frame in json.load(f)['frames'] for url in frame['urls']]
download.fetch(urls + [MOSAICS + name for name in MAPS], out)
