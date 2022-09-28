## this file definse functions to manipulate pixel data:
### plot histograms, adjsut contrast, measure SNR, etc

from typing import Tuple, Union, Any
import glob
import numpy as np
import scipy.stats
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from skimage import io
from skimage.transform import resize
from skimage.util import view_as_blocks
import tifffile as tiff

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


def get_pixel_hist2d(vector_1 : np.array, vector_2 : np.array, bins : int, fig_size : int, xlabel : Union[str, None]=None, ylabel : Union[str, None]=None) -> Tuple[plt.Figure, float, float, float]:
    """
    Plot 2D histogram of two vectors

    Parameters
    ----------
    v1 : np.array
        data vector 1 
    v2 : np.array
        data vector 2
    bins : int
        bins to use for histogram
    fig_size : int
        figure size,  inches
    xlabel : Union[str, None], optional
        x axis label, by default None
    ylabel : Union[str, None], optional
        y axis label, by default None

    Returns
    -------
    Tuple[plt.Figure, float, float, float]
        Figure handles, slope, offset and r value of a linear fit into the data
    """
    fig = plt.figure(figsize = (fig_size,fig_size))
    hist, xedges, yedges = np.histogram2d(vector_1, vector_2, bins)
    hist = hist.T
    plt.imshow(hist, interpolation='nearest', origin='lower',
              extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]], aspect='auto', norm=LogNorm())
    plt.colorbar()

    slope, offset, r_value, _, _ = scipy.stats.linregress(vector_1, vector_2)
    fit_fn = np.poly1d([slope, offset])

    plt.plot(vector_1, fit_fn(vector_1), '--k')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(f"{fit_fn}, R2={np.around(r_value**2, decimals=2)}")
    return fig, slope, offset, r_value

def im_plot(path : str) -> plt.Figure:
    """
    Creates a shows a figure with image at path

    Parameters
    ----------
    path : str
        absolute path to the image to show

    Returns
    -------
    plt.Figure
        handles to the figure
    """    
    im = io.imread(path)
    fig = plt.imshow(im)
    return fig

def plot_all_colormaps(image : np.array, cmaps : list = CMAPS) -> None:
    """
    Visualize all available colormaps

    Parameters
    ----------
    im : np.array
        image to sue to visualize colormaps
    cmaps : list, optional
        list of colormaps to plot
    """
    for cm in cmaps:
        plt.figure(figsize=(6, 6))
        plt.imshow(image, cmap = cm)
        plt.title(f'Colormap: {cm}')
        plt.close()
    return

def average_intensity(path : str) -> np.array:
    """
    Calculates average intensity over eahc plane in teimseries

    Parameters
    ----------
    path : str
        Absolute apht ot the timseries

    Returns
    -------
    np.array
        vector with mean intensity values for each plane 
    """
    image = tiff.imread(glob.glob(path))
    return image.mean(axis=(1,2))

def align_phase(image : np.array, do_align : bool = True, offset : Union[int, None] = None) -> Union[int, np.array]:
    """
    Function to aling line phase in an image generated by a bidirectional scanning 

    Parameters
    ----------
    image : np.array
        2D numpy array representing an image, i.w page of a multipage tiff file
    do_align : bool, optional
        if True - perform image alignment, if False - only onput offset value for image, by default True
    offset : int, optional
        if given, use it to align image, if not - calculate, by default None
    Returns
    -------
    offset : int
        offset calculated or given as input
    image_aligned : np.array
        2D numpy array representing phase-aligned image
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
        if offset > 0:
            # move every line by offset/2
            image_aligned = np.zeros((image.shape[0], int(image.shape[1]+offset)))

            i=0
            while i < len(image)-1: # loop over each pair of lines to insert original data with offset
                image_aligned[i,: -offset] = image[i, :]
                image_aligned[i+1, offset:] = image[i+1]
                i += 2

            image_aligned = image_aligned[:, 1:image_aligned.shape[1]-offset]
            return offset, image_aligned
        else:
            return offset, image
    else:
        return offset

def align_phase_stack(stack : np.array) -> np.array:
    """
        Function to align phase in images in stack: calculate mean offset for all images, 
        apply same value to all images in stack
    Parameters
    ----------
    stack : np.array
        3D numpy array representing stack
    Returns
    -------
    np.array
        3D numpy array representing stack, but aligned
    """
    # calculate mean offset in the stack:
    offsets = []
    for page in stack:
        offset = align_phase(page, do_align = False)
        offsets.append(offset)
    mean_offset = int(np.round(np.mean(offsets)))
    max_offset = np.max(offsets)
    # align all images in stack using mean or max offset: 

    if mean_offset !=0:
        offset = mean_offset
    else:
        offset = max_offset

    stack_aligned = np.zeros((stack.shape[0], stack.shape[1], stack.shape[2]-offset))

    for i, page in enumerate(stack):
        _, page_aligned = align_phase(page, offset = offset)
        stack_aligned[i] = page_aligned
    return stack_aligned

def average_n(array : np.array, downsampling_factor : int) -> np.array:
    """
    Average every N frames of the timeseries
    Parameters
    ----------
    array : np.array
        numpy 3D array
    n : int
        number of rames to average
    Returns
    -------
    np.array
        averaged timeseries
    """    
    reshaped_array = array.reshape(downsampling_factor, int(array.shape[0]/downsampling_factor), array.shape[1], array.shape[2])
    avg_array = reshaped_array.mean(axis=0)
    return avg_array

def image_negative_rescale(data : np.array) -> np.array:  
    """
    Mapping image to non-negative range

    Parameters
    ----------
    data : np.array
        image as a 2D nupmy array

    Returns
    -------
    np.array
        image with pixel values remapped to a non-negative range
    """    
    max_intensity = np.max(data)
    min_intensity = np.min(data)
    data_out = ((data - min_intensity)*2**16/(max_intensity-min_intensity)).astype(np.uint16)
    return data_out

def image_downsample(data : np.array, scaling_factor : int) -> np.array:
    """
    Donwssampling image data according ot the sampling factor

    Parameters
    ----------
    data : np.array
        2d numpy array representing the image
    scaling_factor : int
        scaling factor

    Returns
    -------
    np.array
        downsampled image in a numpy array
    """    
    data_scaled_shape = np.asarray(data.shape / scaling_factor, dtype=int)
    data_scaled = (resize(data, data_scaled_shape)*2**16).astype(np.uint16)
    return data_scaled

def offset_to_zero(image : np.array) -> np.array:
    """
    Offset image to zero

    Parameters
    ----------
    image : np.array
        2D numpyt array representing image

    Returns
    -------
    np.array
        2D numpy array representing offset image
    """    
    imin = image.min()
    im_offset = image-imin
    return im_offset

def compute_contrast(image : np.array, percentile_max : int = 95, percentile_min : int = 5, stack : bool = False) -> float:
    """
    Compute contrast of an image.

    Parameters
    ----------
    image : np.array
        Image to compute contrast of.
    percentile_max : int, optional
        Percentile at which to compute maximum value of the image, by default 95
    percentile_min : int, optional
        Percentile at which to compute minimum value of the image, by default 5
    stack : bool, optional
        Whether input is a stack (tiemseries, 3D array), or a single image (2D array), by default False

    Returns
    -------
    float
        Contrast of the image.
    """    
    if stack:
        i_max = np.percentile(image, percentile_max, axis=2)
        i_min = np.percentile(image, percentile_min, axis=2)
        contrast = (i_max-i_min)/(i_max+i_min)
    else:
        i_max = np.percentile(image, percentile_max)
        i_min = np.percentile(image, percentile_min)
        contrast = (i_max-i_min)/(i_max+i_min)
    return contrast

def compute_acutance(image: np.ndarray, stack : bool = False) -> float:
    """
    Compute the acutance (sharpness) of an image.

    Parameters
    ----------
    image : np.ndarray
        Image to compute acutance of.
    stack : bool, optional
        Whether input is a stack (tiemseries, 3D array), or a single image (2D array), by default False

    Returns
    -------
    float
        Acutance of the image.
    """    
    if stack:
        accutance = []
        for i in range(image.shape[0]):
            for j in range(image.shape[1]):
                block = image[i,j,:,:]
                grady, gradx = np.gradient(block)
                a = (grady ** 2 + gradx ** 2).mean()
                accutance.append(a)
    else:
        grady, gradx = np.gradient(image)
        accutance = (grady ** 2 + gradx ** 2).mean() #to-do: Normalize by mean
    
    return accutance

def compute_basic_snr(image: np.ndarray, stack : bool = False) -> float:
    """
    Compute basic SNR of an image as defined by standard deviation / mean of the image

    Parameters
    ----------
    image : np.ndarray
        Image to compute Basic SNR of.
    stack : bool, optional
        Whether input is a stack (tiemseries, 3D array), or a single image (2D array), by default False

    Returns
    -------
    float
        Basic SNR of an image.
    """    
    if stack: 
        basic_snr = np.std(image, axis=(2,3))/np.mean(image, axis=(2,3))
        return list(basic_snr.flatten())
    else: 
        basic_snr = np.std(image)/np.mean(image)
        return basic_snr

def compute_photon_flux(image: np.ndarray, stack : bool = False) -> float:
    """
    Compute photon flux a 2P image as defined by sqrt(mean pixel valu in image)

    Parameters
    ----------
    image : np.ndarray
        Image to compute phootn flux of.
    stack : bool, optional
        Whether input is a stack (tiemseries, 3D array), or a single image (2D array), by default False

    Returns
    -------
    float
        Photon flux of an image.
    """
    if stack:
        photon_flux = np.sqrt(np.mean(image, axis=(2,3)))
        return list(photon_flux.flatten())
    else:
        photon_flux = np.sqrt(np.mean(image.flatten()))
        return photon_flux

def compute_block_snr(image : np.ndarray, block_shape : tuple, blocks_to_agg : tuple, return_block : bool = False, snr_metric : str = "basic") -> Union[float, tuple]:
    """
    Compute the SNR of nonoverlapping blocks of an image, return aggregate
    SNR from certrain blocks.

    Parameters
    ----------
    image : np.ndarray
        Image to compute SNR of.
    block_shape : tuple
        Shape of blocks to compute SNR of.
    blocks_to_agg : tuple
        Start and end index of block to aggregate SNR (e.g (6,10) will aggregate
        the middle 5 blocks if 16 is chosen).
    return_block : bool, optional
        If True, return the blocks used to compute SNR., by default False
    snr_metric : str, optional
        Type of SNR metric to compute, for now has to be one from thsi list ["basic", "acutance", "photon_flux"], by default "basic"

    Returns
    -------
    Union[float, tuple]
        Mean SNR of blocks.
    """    
    view = view_as_blocks(image, block_shape=block_shape)

    # calculate basic SNR. TODO: add more metrics
    if snr_metric == "basic":
        block_snr = compute_basic_snr(view, stack=True)
    if snr_metric == "photon_flux":
        block_snr = compute_photon_flux(view, stack=True)
    if snr_metric == "acutance":
        block_snr = compute_acutance(view, stack=True)
    
    s,e = blocks_to_agg
    mid_snr_blocks = np.sort(block_snr)[s:e]
    mean_block_snr = np.mean(mid_snr_blocks)

    if return_block:
        return block_snr, mean_block_snr
    else:
        return mean_block_snr
