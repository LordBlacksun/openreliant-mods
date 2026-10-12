"""Downloads what Earth's textures and limb are made from into a folder of its own: NASA's Blue Marble
of 2002 with its clouds and its Black Marble of 2016, the city lights, from NASA's Earth
Observatory, and GOES-18's and GOES-19's full-disk pictures of 21 June 2025 at 21:00 UTC, from
NOAA's open data on Amazon's cloud.

    python3 fetch.py data
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import download  # noqa: E402

BLUE_MARBLE = 'https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57735/land_ocean_ice_cloud_8192.tif'
BLACK_MARBLE = 'https://eoimages.gsfc.nasa.gov/images/imagerecords/144000/144898/BlackMarble_2016_3km.jpg'
GOES = ['https://noaa-goes18.s3.amazonaws.com/ABI-L2-MCMIPF/2025/172/21/'
        'OR_ABI-L2-MCMIPF-M6_G18_s20251722100238_e20251722109552_c20251722110015.nc',
        'https://noaa-goes19.s3.amazonaws.com/ABI-L2-MCMIPF/2025/172/21/'
        'OR_ABI-L2-MCMIPF-M6_G19_s20251722100209_e20251722109518_c20251722109594.nc']

download.fetch([BLUE_MARBLE, BLACK_MARBLE, *GOES], sys.argv[1])
