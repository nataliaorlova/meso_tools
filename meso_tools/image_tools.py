## this file definse functions to manipulate pixel data:
### plot histograms, adjsut contrast, measure SNR, etc

import numpy as np
import scipy.stats
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from skimage import io
import tifffile as tiff
import glob

CMAPS = ['Accent', 'Accent_r', 'Blues', 'Blues_r', 'BrBG', 'BrBG_r', 'BuGn', 'BuGn_r', 'BuPu', 'BuPu_r',
                 'CMRmap', 'CMRmap_r', 'Dark2', 'Dark2_r', 'GnBu', 'GnBu_r', 'Greens', 'Greens_r', 'Greys',
                 'Greys_r', 'OrRd', 'OrRd_r', 'Oranges', 'Oranges_r', 'PRGn', 'PRGn_r', 'Paired', 'Paired_r',
                 'Pastel1', 'Pastel1_r', 'Pastel2', 'Pastel2_r', 'PiYG', 'PiYG_r', 'PuBu', 'PuBuGn', 'PuBuGn_r',
                 'PuBu_r', 'PuOr', 'PuOr_r', 'PuRd', 'PuRd_r', 'Purples', 'Purples_r', 'RdBu', 'RdBu_r', 'RdGy',
                 'RdGy_r', 'RdPu', 'RdPu_r', 'RdYlBu', 'RdYlBu_r', 'RdYlGn', 'RdYlGn_r', 'Reds', 'Reds_r', 'Set1',
                 'Set1_r', 'Set2', 'Set2_r', 'Set3', 'Set3_r', 'Spectral', 'Spectral_r', 'Wistia', 'Wistia_r',
                 'YlGn', 'YlGnBu', 'YlGnBu_r', 'YlGn_r', 'YlOrBr', 'YlOrBr_r', 'YlOrRd', 'YlOrRd_r', 'afmhot',
                 'afmhot_r', 'autumn', 'autumn_r', 'binary', 'binary_r', 'bone', 'bone_r', 'brg', 'brg_r', 'bwr',
                 'bwr_r', 'cividis', 'cividis_r', 'cool', 'cool_r', 'coolwarm', 'coolwarm_r', 'copper', 'copper_r',
                 'cubehelix', 'cubehelix_r', 'flag', 'flag_r', 'gist_earth', 'gist_earth_r', 'gist_gray',
                 'gist_gray_r', 'gist_heat', 'gist_heat_r', 'gist_ncar', 'gist_ncar_r', 'gist_rainbow',
                 'gist_rainbow_r', 'gist_stern', 'gist_stern_r', 'gist_yarg', 'gist_yarg_r', 'gnuplot',
                 'gnuplot2', 'gnuplot2_r', 'gnuplot_r', 'gray', 'gray_r', 'hot', 'hot_r', 'hsv', 'hsv_r',
                 'inferno', 'inferno_r', 'jet', 'jet_r', 'magma', 'magma_r', 'nipy_spectral', 'nipy_spectral_r',
                 'ocean', 'ocean_r', 'pink', 'pink_r', 'plasma', 'plasma_r', 'prism', 'prism_r', 'rainbow',
                 'rainbow_r', 'seismic', 'seismic_r', 'spring', 'spring_r', 'summer', 'summer_r', 'tab10',
                 'tab10_r', 'tab20', 'tab20_r', 'tab20b', 'tab20b_r', 'tab20c', 'tab20c_r', 'terrain',
                 'terrain_r', 'twilight', 'twilight_r', 'twilight_shifted', 'twilight_shifted_r', 'viridis',
                 'viridis_r', 'winter', 'winter_r']

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

def im_plot(path):
    im = io.imread(path)
    fig = plt.imshow(im)
    return fig

def plot_all_colormaps(im):
    for cm in CMAPS:
        plt.figure(figsize=(6, 6))
        plt.imshow(im, cmap = cm)
        plt.title(f'Colormap: {cm}')
        plt.close()
    return

def average_intensity(filepath):
    """
    Inputs the filepath of the lightleak.tiff file and outputs the average pixel value for each frame in the .tiff
    """
    im = tiff.imread(glob.glob(filepath))
    intensity = []
    for frame in range(len(im)):
        x = im[frame].mean(axis=0)
        x = x.mean(axis = 0)
        intensity.append(x)
    return np.array(intensity)

def aling_phase(image, do_align = True, offset = None):
    """
    function to aling line phase in an image generated by a bidirectional scanning 
    Inputs:
        image: 2D numpy array representing an image, i.w page of a multipage tiff file
        do_align: bool : if True - perform image alignment, if False - only onput offset value for image
        offset: int : if given, use it to align image, if not - calculate
    Return:
        offset : int : offset calculated or given as input
        image_aligned : 2D numpy array representing phase-aligned image
    """
    
    if not offset : 
        # calculate mean offset in the frame:
        offsets = []
        i=1 
        while i < len(image)-1 : # loop over each pair of lines to calculate pairwise correlation
            offset = image.shape[0]/2 - np.argmax(np.correlate(image[i], image[i+1], mode='same'))
            offsets.append(offset)
            i += 2
        offset = int(np.round(np.mean(offsets)))

    if do_align: 
        # move every line by offset/2
        image_aligned = np.zeros((image.shape[0], int(image.shape[1]+offset)))

        i=0
        while i < len(image)-1: # loop over each pair of lines to insert original data with offset
            image_aligned[i, :-offset] = image[i, :]
            image_aligned[i+1, offset:] = image[i+1]
            i += 2

        image_aligned = image_aligned[:, 1:image_aligned.shape[1]-offset]
        return offset, image_aligned
    else:
        return offset

def align_phase_stack(stack):
    """
    fucntion to align phase in images in stack: calculate mean offset for all images, 
        apply same value to all images in stack
    Inputs:
        stack: 3D numpy array representing stack
    Returns:
        stack_aligned: 3D numpy array representing stack, but aligned
    """
    # calculate mean offset in the stack:
    offsets = []
    for page in stack:
        offset = aling_phase(page, do_align = False)
        offsets.append(offset)
    offset = int(np.round(np.mean(offsets)))
    
    # align all images in stack using mean offset: 
    stack_aligned = np.zeros((stack.shape[0], stack.shape[1], stack.shape[2]-offset+1))

    for i, page in enumerate(stack):
        _, page_aligned = aling_phase(page, offset = offset)
        stack_aligned[i] = page_aligned
    
    return stack_aligned

def average_n(array, n):
    """averages every N frames of the timeseries
    Input:
        array: numpy 3D array
        n: int: number of rames to average
    Return:
        averaged timeseries
    """
    reshaped_array = array.reshape(n, int(array.shape[0]/n), array.shape[1], array.shape[2])
    avg_array = reshaped_array.mean(axis=0)
    return avg_array