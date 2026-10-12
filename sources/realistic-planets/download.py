"""Downloads files into a folder, each once, for the bodies' fetch scripts."""
import json
import os
import urllib.request

# Karkoschka's 1993 albedo spectra of the giant planets and Titan, and their label, from the PDS
# Atmospheres Node.
KARKOSCHKA = ['https://atmos.nmsu.edu/pdsd/archive/data/eso-jsnu-spectrophotometer-4-v20/gbat_0001/data/' + name
              for name in ('1993.tab', '1993.lbl')]


def listed(listings):
    """The download links of every frame that the frame listings, JSON files, name, in their
    order."""
    urls = []
    for listing in listings:
        with open(listing) as f:
            urls += [url for frame in json.load(f)['frames'] for url in frame['urls']]
    return urls


def fetch(urls, out):
    """Downloads each of `urls` into the folder `out`, unless a file of its name is there already."""
    os.makedirs(out, exist_ok=True)
    for n, url in enumerate(urls, 1):
        path = os.path.join(out, os.path.basename(url))
        if not os.path.exists(path):
            urllib.request.urlretrieve(url, path)
        print(f"{n}/{len(urls)} {os.path.basename(url)}", flush=True)
