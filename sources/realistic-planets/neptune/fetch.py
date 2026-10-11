"""Downloads what Neptune's texture is made from into a folder of its own: each frame's GEOMED image
and label that frames.json lists, from the PDS Ring-Moon Systems Node, and Karkoschka's 1993 albedo
spectra of the giant planets, from the PDS Atmospheres Node.

    python3 fetch.py frames.json data
"""
import json
import os
import sys
import urllib.request

KARKOSCHKA = 'https://atmos.nmsu.edu/pdsd/archive/data/eso-jsnu-spectrophotometer-4-v20/gbat_0001/data/'

listing, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
urls = [u for frame in json.load(open(listing))['frames'] for u in frame['urls']]
urls += [KARKOSCHKA + '1993.tab', KARKOSCHKA + '1993.lbl']
for n, url in enumerate(urls, 1):
    path = os.path.join(out, os.path.basename(url))
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    print(f"{n}/{len(urls)} {os.path.basename(url)}", flush=True)
