"""
This file contains functions for importing and handling APOGEE and related
datasets. If run as a script, it will re-generate the main sample file
(src/data/APOGEE/sample.csv).
"""

import urllib.request
from pathlib import Path
import numpy as np
import pandas as pd
import paths
from utils import fits_to_pandas, box_smooth, kde2D

# Data file names
ALLSTAR_FNAME = 'allStarLite-dr17-synspec_rev1.fits'
LEUNG23_FNAME = 'nn_latent_age_dr17.csv'
# List of columns to include in the final sample
SAMPLE_COLS = ['APOGEE_ID', 'RA', 'DEC', 'GALR', 'GALPHI', 'GALZ', 'SNREV',
               'TEFF', 'TEFF_ERR', 'LOGG', 'LOGG_ERR', 'FE_H', 'FE_H_ERR',
               'O_FE', 'O_FE_ERR', 'LATENT_AGE', 'LATENT_AGE_ERR', 
               'LOG_LATENT_AGE', 'LOG_LATENT_AGE_ERR',
               'GAIAEDR3_R_LO_PHOTOGEO', 'GAIAEDR3_R_MED_PHOTOGEO', 'GAIAEDR3_R_HI_PHOTOGEO']

def main():
    apogee_data = import_apogee(overwrite=True, verbose=True)
    print(apogee_data)


def gen_kde(data, bandwidth=0.02, absz_lim=(0, 5), galr_lim=(0, 20), 
            overwrite=False, savedir=paths.data/'APOGEE/kde/ofe_feh/',
            xcol='FE_H', ycol='O_FE'):
    """
    Generate kernel density estimate (KDE) of APOGEE data, or import previously
    saved KDE if it already exists.
    
    Parameters
    ----------
    data : pandas.DataFrame
        APOGEE or MWM data.
    bandwidth : float, optional
        Kernel density estimate bandwidth. A larger number will produce
        smoother contour lines. The default is 0.02.
    absz_lim : tuple, optional
        Limits on absolute Galactic z-height in kpc. The default is (0, 5).
    galr_lim : tuple, optional
        Limits on Galactocentric radius in kpc. The default is (0, 20).
    overwrite : bool, optional
        If True, force re-generate the 2D KDE and save the output.
    savedir : path, optional
        Directory to save the KDE outputs. The default is 
        src/data/APOGEE/kde/ofe_feh/.
    xcol : str, optional
        Name of column with x-axis data. The default is 'FE_H'.
    ycol : str, optional
        Name of column with y-axis data. The default is 'O_FE'.
    
    Returns
    -------
    xx, yy, logz: tuple of numpy.array
        Outputs of kde2D()
    """
    # Path to save 2D KDE for faster plot times
    path = kde_path(galr_lim, absz_lim, savedir=savedir)
    if path.exists() and not overwrite:
        xx, yy, logz = read_kde(path)
    else:
        # Limit to specified Galactic region
        subset = apogee_region(data, galr_lim, absz_lim)
        subset = subset.copy().dropna(axis=0, subset=[xcol, ycol])
        xx, yy, logz = kde2D(subset[xcol], subset[ycol], bandwidth)
        save_kde(xx, yy, logz, path)
    return xx, yy, logz


def read_kde(path):
    """
    Read a text file generated by save_kde()
    """
    arr2d = np.genfromtxt(path)
    nrows = int(arr2d.shape[0]/3)
    xx = arr2d[:nrows]
    yy = arr2d[nrows:2*nrows]
    logz = arr2d[2*nrows:]
    return xx, yy, logz


def save_kde(xx, yy, logz, path):
    """
    Generate a text file containing the KDE of the given region along with its
    corresponding x and y coordinates.
    """
    if not path.parents[0].is_dir():
        path.parents[0].mkdir(parents=True)
    with open(path, 'w') as f:
        for arr in [xx, yy, logz]:
            f.write('#\n')
            np.savetxt(f, arr)


def kde_path(galr_lim, absz_lim, savedir=paths.data/'APOGEE/kde'):
    """
    Generate file name for the KDE of the given region.
    """
    filename = 'r%s-%s_z%s-%s.dat' % (galr_lim[0], galr_lim[1],
                                      absz_lim[0], absz_lim[1])
    return Path(savedir) / filename
    

def apogee_mdf(data, col='FE_H', bins=100, range=None, smoothing=0.):
    """
    Calculate the MDF in [Fe/H] of a region of APOGEE data.
    
    Parameters
    ----------
    data : pandas.DataFrame
        Data from APOGEE DR17.
    col : str, optional
        Column name of desired abundance data. The default is 'FE_H'.
    bins : int or sequence of scalars, optional
        If an int, defines the number of equal-width bins in the given
        range. If a sequence, defines the array of bin edges including
        the right-most edge. The default is 100.
    range : tuple, optional
        Range in the given column to bin. The default is None, which 
        corresponds to the entire range of data. If bins is provided as
        a sequence, range is ignored.
    smoothing : float, optional
        Width of boxcar smoothing in x-axis units. If 0, the distribution will
        not be smoothed. The default is 0.
    
    Returns
    -------
    mdf : numpy.ndarray
        Boxcar-smoothed MDF.
    bin_edges : numpy.ndarray
        [Fe/H] bins including left and right edges, of length len(mdf)+1.
    """
    mdf, bin_edges = np.histogram(data[col], bins=bins, range=range, 
                                  density=True)
    if smoothing > 0.:
        mdf = box_smooth(mdf, bin_edges, smoothing)
    return mdf, bin_edges


def apogee_region(data, galr_lim=(3, 15), absz_lim=(0, 2)):
    """
    Slice APOGEE data within a given Galactic region of radius and z-height.

    Parameters
    ----------
    data : pandas DataFrame
        APOGEE data
    galr_lim : tuple
        Minimum and maximum Galactic radius in kpc
    absz_lim : tuple
        Minimum and maximum of the absolute value of z-height in kpc

    Returns
    -------
    pandas DataFrame
        Re-indexed DataFrame of stellar parameters
    """
    galr_min, galr_max = galr_lim
    absz_min, absz_max = absz_lim
    # Select subset
    subset = data[(data['GALR'] >= galr_min) &
                  (data['GALR'] < galr_max) &
                  (data['GALZ'].abs() >= absz_min) &
                  (data['GALZ'].abs() < absz_max)].copy()
    subset.reset_index(inplace=True, drop=True)
    return subset


def import_apogee(name='sample.csv', parent_dir=paths.data/'APOGEE', 
                  verbose=False, overwrite=False):
    """
    Import combined and cut sample of APOGEE data, generating first if needed.
    
    Parameters
    ----------
    name : str, optional
        Name of CSV file containing sample data. The default is 'sample.csv'.
    parent_dir : str or pathlib.Path, optional
        The parent directory containing APOGEE data files. The default is
        '../data/APOGEE/'.
    verbose : bool, optional
        Whether to print verbose output to terminal. The default is False.
    overwrite : bool, optional
        If True, re-generates the sample file even if it already exists.
        The default is False.

    Returns
    -------
    df : pandas.DataFrame
        DataFrame containing combined and cut sample of APOGEE data.
    """
    sample_file_path = parent_dir / name
    if sample_file_path.exists() and not overwrite:
        if verbose:
            print('Reading APOGEE sample from', sample_file_path)
        df = pd.read_csv(sample_file_path)
    else:
        if verbose:
            print('Sample file at', sample_file_path, 'not found.\n' + \
                  'Importing APOGEE catalog and generating sample...')
        df = gen_apogee_sample(parent_dir=parent_dir, verbose=verbose)
        df.to_csv(sample_file_path, index=False)
        if verbose:
            print('Done.')
    return df


def gen_apogee_sample(parent_dir=paths.data/'APOGEE', verbose=False):
    """
    Make selection cuts to APOGEE sample and combine with age catalogs.
    
    Parameters
    ----------
    parent_dir : str or pathlib.Path, optional
        The parent directory containing APOGEE data files. The default is
        '../data/APOGEE/'.
    verbose : bool, optional
        Whether to print verbose output to terminal. The default is False.
    
    Returns
    -------
    sample : pandas.DataFrame
    """
    # Make parent dir if needed
    if not Path(parent_dir).is_dir():
        parent_dir.mkdir(parents=True)
    apogee_catalog_path = parent_dir / ALLSTAR_FNAME
    if not apogee_catalog_path.is_file():
        # Download DR17 allStar file from SDSS server
        if verbose: 
            print('Downloading allStar file (this will take a few minutes)...')
        get_allStar_dr17()
    if verbose: print('Importing allStar file...')
    apogee_catalog = fits_to_pandas(apogee_catalog_path, hdu=1)
    # Add ages from row-matched datasets BEFORE any cuts
    # Add ages from Leung et al. (2023)
    leung23_catalog_path = parent_dir / LEUNG23_FNAME
    if not leung23_catalog_path.is_file():
        # Download Leung+ 2023 data from GitHub
        if verbose:
            print('Downloading Leung et al. (2023) age data...')
        get_Leung2023_ages()
    if verbose: print('Joining with latent age catalog...')
    leung23_catalog = pd.read_csv(leung23_catalog_path)
    full_catalog = join_latent_ages(apogee_catalog, leung23_catalog)
    if verbose: print('Implementing quality cuts...')
    sample = apogee_quality_cuts(full_catalog)
    # Calculate galactocentric coordinates based on galactic l, b and Gaia dist
    galr, galphi, galz = galactic_to_galactocentric(
        sample['GLON'], sample['GLAT'], sample['GAIAEDR3_R_MED_PHOTOGEO']/1000
    )
    sample['GALR'] = galr # kpc
    sample['GALPHI'] = galphi # deg
    sample['GALZ'] = galz # kpc
    # Limit by galactocentric radius and z-height
    sample = sample[(sample['GALR'] > 3) & (sample['GALR'] < 15) &
                    (sample['GALZ'].abs() < 2)]
    sample.reset_index(inplace=True, drop=True)
    # Drop unneeded columns
    return sample[SAMPLE_COLS].copy()


def join_latent_ages(apogee_df, leung23_df):
    """
    Join ages from Leung et al. (2023) to the row-matched APOGEE dataset.
    
    Parameters
    ----------
    apogee_df : pandas.DataFrame
        Full APOGEE dataset without cuts
    leung23_df : pandas.DataFrame
        Dataset from Leung et al. (2023)
    
    Returns
    -------
    joined_df : pandas.DataFrame
        APOGEE dataset with latent ages
    """
    cols = ['LogAge', 'LogAge_Error', 'Age', 'Age_Error']
    latent_ages = leung23_df[cols].copy()
    latent_ages.columns = ['LOG_LATENT_AGE', 'LOG_LATENT_AGE_ERR', 
                           'LATENT_AGE', 'LATENT_AGE_ERR']
    # Limit to stars with <40% age uncertainty per recommendation
    frac_err = latent_ages['LATENT_AGE_ERR'] / latent_ages['LATENT_AGE']
    latent_ages.where(frac_err < 0.4, inplace=True)
    joined = apogee_df.join(latent_ages)
    return joined


def apogee_quality_cuts(df):
    """
    Make quality cuts on the APOGEE catalog.
    
    Parameters
    ----------
    df : pandas.DataFrame
        Full APOGEE catalog
    
    Returns
    -------
    pandas.DataFrame
    """
    # Limit to main red star sample
    df = df[df['EXTRATARG'] == 0]
    # Weed out bad flags
    fatal_flags = (2**23) # STAR_BAD
    df = df[df['ASPCAPFLAG'] & fatal_flags == 0]
    # Cut low-S/N targets
    df = df[df['SNREV'] > 80]
    # Limit to giants
    df = df[(df['LOGG'] > 1) & (df['LOGG'] < 3.8) & 
            (df['TEFF'] > 3500) & (df['TEFF'] < 5500)]
    # Replace NaN stand-in values with NaN
    df.replace(99.999, np.nan, inplace=True)
    # Limit to stars with measurements of both [Fe/H] and [O/Fe]
    df.dropna(subset=['FE_H', 'O_FE'], inplace=True)
    df.reset_index(inplace=True, drop=True)
    return df
    

def galactic_to_galactocentric(l, b, distance):
    r"""
    Use astropy's SkyCoord to convert Galactic (l, b, distance) coordinates
    to galactocentric (r, phi, z) coordinates.

    Parameters
    ----------
    l : array-like
        Galactic longitude in degrees
    b : array-like
        Galactic latitude in degrees
    distance : array-like
        Distance (from Sun) in kpc

    Returns
    -------
    galr : numpy array
        Galactocentric radius in kpc
    galphi : numpy array
        Galactocentric phi-coordinates in degrees
    galz : numpy arraay
        Galactocentric z-height in kpc
    """
    import astropy.units as u
    from astropy.coordinates import SkyCoord, Galactic, Galactocentric
    l = np.array(l)
    b = np.array(b)
    d = np.array(distance)
    if l.shape == b.shape == d.shape:
        if not isinstance(l, u.quantity.Quantity):
            l *= u.deg
        if not isinstance(b, u.quantity.Quantity):
            b *= u.deg
        if not isinstance(d, u.quantity.Quantity):
            d *= u.kpc
        galactic = SkyCoord(l=l, b=b, distance=d, frame=Galactic())
        galactocentric = galactic.transform_to(frame=Galactocentric())
        galactocentric.representation_type = 'cylindrical'
        galr = galactocentric.rho.to(u.kpc).value
        galphi = galactocentric.phi.to(u.deg).value
        galz = galactocentric.z.to(u.kpc).value
        return galr, galphi, galz
    else:
        raise ValueError('Arrays must be of same length.')


def get_allStar_dr17():
    """
    Retrieve the DR17 ASPCAP allStarLite file from the SDSS data server.
    """
    url = 'https://data.sdss.org/sas/dr17/apogee/spectro/aspcap/dr17/synspec_rev1/%s' \
        % ALLSTAR_FNAME
    with urllib.request.urlopen(url) as response:
        fits = response.read()
    with open(paths.data / 'APOGEE' / ALLSTAR_FNAME, 'wb') as f:
        f.write(fits)
        

def get_Leung2023_ages():
    """
    Retrieve the database of latent ages from Leung et al. (2023).
    """
    import gzip
    url = 'https://raw.githubusercontent.com/henrysky/astroNN_ages/main/%s.gz' % LEUNG23_FNAME
    with urllib.request.urlopen(url) as response:
        zipped = response.read()
    csv = gzip.decompress(zipped)
    with open(paths.data / 'APOGEE' / LEUNG23_FNAME, 'wb') as f:
        f.write(csv)


if __name__ == '__main__':
    main()
