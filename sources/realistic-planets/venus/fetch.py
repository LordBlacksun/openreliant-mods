"""Downloads what Venus's texture and limb are made from into a folder of its own: thirteen of
Akatsuki's ultraviolet maps of Venus's cloud tops, at 365 nm, from 25 to 29 June 2022, from JAXA's
DARTS archive, and six sets of Venus Express's pictures at 365, 513 and 965 nm, with their geometry,
from ESA's Planetary Science Archive.

    python3 fetch.py data
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import download  # noqa: E402

UVI = 'https://data.darts.isas.jaxa.jp/pub/pds3/extras/vco_uvi_l3_v1.1/vcouvi_7009/data/l3b/netcdf/r0218/uvi_{}_365_l3b_v21.nc'
# About 8 hours apart, over about one turn of the cloud tops.
TIMES = ['20220625_070444', '20220625_150446', '20220625_210446', '20220626_070446', '20220626_150444',
         '20220626_210446', '20220627_070445', '20220627_150446', '20220627_210449', '20220628_070446',
         '20220628_170446', '20220629_010446', '20220629_090445']
VMC = 'https://archives.esac.esa.int/psa/ftp/VENUS-EXPRESS/VMC/VEX-V-VMC-3-RDR-V3.0'
# Each set's orbit and the numbers of its pictures at 365, 965 and 513 nm.
SETS = [('0441', (34, 35, 37)), ('0441', (38, 39, 41)), ('0457', (30, 31, 33)), ('0457', (34, 35, 37)),
        ('0470', (58, 59, 61)), ('0470', (66, 67, 69))]

frames = [f"V{orbit}_{number:04d}_{band}" for orbit, numbers in SETS for number, band in zip(numbers, ('UV2', 'N12', 'VI2'))]
download.fetch([UVI.format(t) for t in TIMES]
               + [f"{VMC}/DATA/{frame[1:5]}/{frame}.IMG" for frame in frames]
               + [f"{VMC}/GEOMETRY/{frame[1:5]}/{frame}.GEO" for frame in frames], sys.argv[1])
