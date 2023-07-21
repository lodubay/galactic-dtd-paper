"""
Compare [O/Fe]-[Fe/H] plots for the Solar annulus for VICE outputs with
different star formation histories and delay time distributions
"""

from tqdm import tqdm
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
# from matplotlib.colors import Normalize
# from matplotlib.cm import ScalarMappable
import vice
from multizone_stars import MultizoneStars
from scatter_plot_grid import setup_colorbar
from apogee_tools import import_apogee, gen_kde
from _globals import ZONE_WIDTH, TWO_COLUMN_WIDTH, MAX_SF_RADIUS, ABSZ_BINS
import paths

FEH_LIM = (-1.3, 0.6)
OFE_LIM = (-0.15, 0.55)
GALR_LIM = (7, 9)

SFH_MODEL = 'insideout'
DTD_LIST = ['prompt', 
            'powerlaw_slope11', 
            'exponential_timescale15', 
            'plateau_width10', 
            'triple']
DTD_LABELS = ['Two-population', 
              'Power-law\n($\\alpha=-1.1$)', 
              'Exponential\n($\\tau=1.5$ Gyr)',
              'Plateau\n($W=1$ Gyr)',
              'Triple-system']

CMAP_NAME = 'winter'

def main():
    # Set up figure
    plt.style.use(paths.styles / 'paper.mplstyle')
    width = TWO_COLUMN_WIDTH
    fig, axs = plt.subplots(3, 5, sharex=True, sharey=True,
                            figsize=(width, 3/5*width))
    plt.subplots_adjust(top=0.92, right=0.98, left=0.06, bottom=0.08, 
                        wspace=0., hspace=0.)
    cbar = setup_colorbar(fig, cmap=CMAP_NAME, vmin=0, vmax=MAX_SF_RADIUS,
                          label=r'Birth $R_{\rm{gal}}$ [kpc]')
    cbar.ax.yaxis.set_major_locator(MultipleLocator(2))
    cbar.ax.yaxis.set_minor_locator(MultipleLocator(0.5))
    
    apogee_data = import_apogee()
    
    for j, dtd in enumerate(DTD_LIST):
        output_name = '/'.join(['gaussian', SFH_MODEL, dtd, 'diskmodel'])
        # Import multioutput stars data
        mzs = MultizoneStars.from_output(output_name)
        mzs.model_uncertainty(inplace=True)
        for i in range(len(ABSZ_BINS) - 1):
            absz_lim = (ABSZ_BINS[-(i+2)], ABSZ_BINS[-(i+1)])
            vice_subset = mzs.region(GALR_LIM, absz_lim)
            # Plot sample of star particle abundances
            vice_subset.scatter_plot(axs[i,j], '[fe/h]', '[o/fe]', 
                                     color='galr_origin', markersize=0.1,
                                     cmap=CMAP_NAME, norm=cbar.norm)
            # Plot APOGEE contours
            apogee_contours(axs[i,j], apogee_data, GALR_LIM, absz_lim)
            # Plot abundance tracks
            zone = int(0.5 * (GALR_LIM[0] + GALR_LIM[1]) / ZONE_WIDTH)
            zone_path = str(mzs.fullpath / ('zone%d' % zone))
            hist = vice.history(zone_path)
            axs[i,j].plot(hist['[fe/h]'], hist['[o/fe]'], c='k', ls='-', 
                          linewidth=0.5)
    
    # Set x-axis ticks
    axs[0,0].xaxis.set_major_locator(MultipleLocator(0.5))
    axs[0,0].xaxis.set_minor_locator(MultipleLocator(0.1))
    # Set y-axis ticks
    axs[0,0].yaxis.set_major_locator(MultipleLocator(0.2))
    axs[0,0].yaxis.set_minor_locator(MultipleLocator(0.05))
    # Set axis limits
    axs[0,0].set_xlim(FEH_LIM)
    axs[0,0].set_ylim(OFE_LIM)
    # Set axis labels
    for ax in axs[-1]:
        ax.set_xlabel('[Fe/H]')
    for i, ax in enumerate(axs[:,0]):
        ax.set_ylabel('[O/Fe]', labelpad=2)
        absz_lim = (ABSZ_BINS[-(i+2)], ABSZ_BINS[-(i+1)])
        ax.text(0.93, 0.93, r'$%s\leq |z| < %s$ kpc' % absz_lim, 
                va='top', ha='right', transform=ax.transAxes)
    for j, ax in enumerate(axs[0]):
        ax.set_title(DTD_LABELS[j])
    
    plt.savefig(paths.figures / 'ofe_feh_dtd.pdf', dpi=300)
    plt.close()


def apogee_contours(ax, apogee_data, galr_lim=(0, 20), absz_lim=(0, 3)):
    xx, yy, logz = gen_kde(apogee_data, bandwidth=0.02,
                           galr_lim=GALR_LIM, absz_lim=absz_lim)
    # scale the linear density to the max value
    scaled_density = np.exp(logz) / np.max(np.exp(logz))
    # contour levels at 1 and 2 sigma
    levels = np.exp(-0.5 * np.array([2, 1])**2)
    ax.contour(xx, yy, scaled_density, levels, colors='r',
               linewidths=0.5, linestyles=['--', '-'])


if __name__ == '__main__':
    main()
