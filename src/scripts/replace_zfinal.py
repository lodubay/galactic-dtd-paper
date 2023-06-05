# -*- coding: utf-8 -*-
"""
This script replaces the old zfinal values in VICE multizone outputs with
the new calculation (Gaussian migration scheme only).
"""

from pathlib import Path
import paths
import pandas as pd
import numpy as np
import random
from tqdm import tqdm
import vice
from _globals import ZONE_WIDTH
import math as m

def main():
    p = paths.data / 'migration' / 'gaussian'
    for filepath in list(p.glob('**/*_analogdata.out')):
        print(filepath)
        output_name = '/'.join(str(filepath).split('/')[-3:]).split('_analogdata')[0]
        stars = multioutput_to_pandas(output_name)
        analogdata = pd.read_csv(filepath, sep='\t')
        
        assert(analogdata.shape[0] == stars.shape[0])
        
        zfinal_arr = np.arange(-5, 5.01, 0.01)
        samples = []
        for i in tqdm(range(stars.shape[0])):
            hz = sech_scale(stars['age'].iloc[i], stars['galr_final'].iloc[i])
            z = inv_sech_cdf(random.random(), hz)
            samples.append(z)
        analogdata['zfinal'] = np.array(samples)
        
        analogdata.to_csv(filepath, sep='\t')
        
        
def sech_scale(age, rfinal):
    return 0.25 * np.exp((age - 5)/7.0) * np.exp((rfinal-8)/6.0)

def sech_dist(z, scale):
    return 1/(4 * scale) * np.cosh(z / (2 * scale))**-2

def sech_cdf(z, scale):
    return 1 / (1 + np.exp(-z / scale))

def inv_sech_cdf(cdf, scale):
    return -scale * m.log(1/cdf - 1)

def multioutput_to_pandas(output_name, data_dir=paths.data/'migration', 
                          verbose=False, zone_width=ZONE_WIDTH):
    """
    Convert VICE multizone stars output to pandas DataFrame (slow).

    Parameters
    ----------
    output_name : str
        Path to the .vice directory containing the migration simulation output
    data_dir : str, optional
        Path to the parent directory of all migration outputs. The default is
        '../data/migration_outputs'.
    verbose : bool, optional
        If True, print verbose output to terminal.

    Returns
    -------
    pandas DataFrame
        Parameters of simulated stellar populations including galactic z-height
    """
    full_path = Path(data_dir) / output_name
    if verbose: 
        print('Importing VICE multizone data from %s.vice' % full_path)
    output = vice.output(str(full_path))
    stars = pd.DataFrame(dict(output.stars))
    analogdata = pd.read_csv('%s_analogdata.out' % full_path, sep='\t')
    # Combine relevant data
    stars[['analog_id', 'zfinal']] = analogdata[['analog_id', 'zfinal']]
    # Convert zone to radius
    stars['galr_origin'] = stars['zone_origin'] * zone_width
    stars['galr_final'] = stars['zone_final'] * zone_width
    return stars
        
    
if __name__ == '__main__':
    main()