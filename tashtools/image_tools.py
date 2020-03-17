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


def plot_psd():
    # plot traces for 5 selected ROIs:

    for cell in roi_idx_5:
        # plot 2000 timepoints :
        gt_trace = gt_traces.loc[cell].trace[100:1000]
        gtn_trace = gtn_traces.loc[cell].trace[100:1000]
        den_trace = den_traces.loc[cell].trace[100 - 30:1000 - 30]

        gt_mean = np.mean(gt_trace)
        gtn_mean = np.mean(gtn_trace)
        den_mean = np.mean(den_trace)

        gt_trace_debiased = gt_trace - gt_mean
        gtn_trace_debiased = gtn_trace - gtn_mean
        den_trace_debiased = den_trace - den_mean

        # rolling average
        N = 15
        gtn_mov_avg = runningMeanFast(gtn_trace_debiased, N)

        # loess filter
        f = 0.016
        x = np.linspace(0, len(gtn_trace_debiased), len(gtn_trace_debiased))
        gtn_lowess = lowess_ag(x, gtn_trace_debiased, f=f, iter=1)
        gtn_lowess_mad = np.round(mad(gtn_lowess), 2)

        # median absolute deviation:
        gt_mad = np.round(mad(gt_trace), 2)
        gtn_mad = np.round(mad(gtn_trace), 2)
        den_mad = np.round(mad(den_trace), 2)
        gtn_mov_avg_mad = np.round(mad(gtn_mov_avg), 2)

        plt.figure(figsize=(20, 6))
        plt.grid(color='black', linestyle='-', linewidth=0.5)
        plt.plot(gtn_trace_debiased, 'tomato', label=f'noisy, m.a.d. = {gtn_mad}')
        plt.plot(den_trace_debiased, 'maroon', label=f'denoised, m.a.d. = {den_mad}')
        plt.plot(gt_trace_debiased * 100, 'green', label=f'ground truth, m.a.d. = {gt_mad}')
        plt.plot(gtn_mov_avg, 'cyan', label=f'rolling avg, N={N}, m.a.d. = {gtn_mov_avg_mad}')
        plt.plot(gtn_lowess, 'gold',
                 label=f'loess, N = {int(ceil(len(gtn_trace_debiased) * f))}, m.a.d. = {gtn_lowess_mad}')

        plt.xlabel('time, ms')
        plt.ylabel('fluorescence, i.u.')
        plt.title(f'Traces for cell # {cell}')
        plt.legend()
        save_path = f"/media/rd-storage/X/Denoising/denoised_simulation/figures/teh_comp/{TODAY}_techniques_traces_cell_{cell}.png"
        plt.savefig(save_path, bbox_inches='tight')

        plt.close()

        plt.figure(figsize=(20, 6))
        plt.grid(color='black', linestyle='-', linewidth=0.5)
        dt = np.pi / 100.
        fs = 1. / dt
        t = np.arange(0, len(gtn_trace_debiased), dt)
        plt.psd(gtn_trace_debiased, NFFT=len(t) // 2, pad_to=len(t), noverlap=0, Fs=fs, color='tomato', label=f'noisy')
        plt.psd(den_trace_debiased, NFFT=len(t) // 2, pad_to=len(t), noverlap=0, Fs=fs, color='maroon',
                label=f'denoised')
        plt.psd(gt_trace_debiased * 100, NFFT=len(t) // 2, pad_to=len(t), noverlap=0, Fs=fs, color='green',
                label=f'ground truth')
        plt.psd(gtn_mov_avg, NFFT=len(t) // 2, pad_to=len(t), noverlap=0, Fs=fs, color='cyan',
                label=f'rolling avg, N={N}')
        plt.psd(gtn_lowess, NFFT=len(t) // 2, pad_to=len(t), noverlap=0, Fs=fs, color='gold',
                label=f'loess, N = {int(ceil(len(gtn_trace_debiased) * f))}')

        plt.xlabel('frequency')
        plt.ylabel('fluorescence, i.u.')
        plt.title(f'power spectrum density for # {cell}')
        plt.legend()
        save_path = f"/media/rd-storage/X/Denoising/denoised_simulation/figures/teh_comp/{TODAY}_techniques_psd_cell_{cell}.png"
        plt.savefig(save_path, bbox_inches='tight')