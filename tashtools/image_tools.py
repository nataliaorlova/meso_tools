import numpy as np
import scipy.stats
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm


def get_pixel_hist2d(x, y, xlabel=None, ylabel=None):
    fig = plt.figure(figsize=(10,10))
    H, xedges, yedges = np.histogram2d(x, y, bins=(30, 30))
    H = H.T
    plt.imshow(H, interpolation='nearest', origin='low',
              extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]], aspect='auto', norm=LogNorm())
    plt.colorbar()

    slope, offset, r_value, p_value, std_err = scipy.stats.linregress(x, y)
    fit_fn = np.poly1d([slope, offset])

    plt.plot(x, fit_fn(x), '--k')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title('%s    R2=%.2f'%(fit_fn, r_value**2))
    return fig, slope, offset, r_value
