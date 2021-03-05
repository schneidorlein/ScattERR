"""
Plot module of the MyUtil utility package to standardize matplotlib plotting properties

Dynamically writes the rcParameters of the matplotlib package

example:
  from MyUtil import Plot
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


### global variables, latex document and pdftex properties
_textwidth = 455            # text width in pt
_dpi = 72.256               # resolution, dots per inch


def load_defaults(sf=2.0, mode='thesis'):
    """
    Loads customized matplotlib figure plotting properties.
    Properties (figuresize, textsize, ticksize, linewidth, ...) scale with scaling factor 'sf'  

    usage:
        import matplotlib.pyplot as plt     
        from MyUtil import Plot 
        Plot.load_defaults(3.0) #load before all pyplot operations
        Plot.use_tex(True) #use \mathrm{} to get non-italic text in math mode

        ...
        fig = plt.figure()
        ...
        plt.show()
    """ 

    ### check if mode is valid
    modes_allowed = ['thesis', 'thesis_half','ct']
    if not mode in modes_allowed:
        print ("Error! Unknown mode '%s'! rcParameters not updated! Choose from %s" %(mode, modes_allowed))
        return -1

    if mode == 'thesis':
        ### font sizes
        fs_big = 14          # size of big letters in pt
        fs_med = 12
        fs_small = 10       # size of small letters pt
        ### subplot margins
        sp_t = 0.94     # ratio for top of subfigure in figure 
        sp_b = 0.12     # ratio for bottom of subfigure in figure 
        sp_l = 0.10     # ratio for left margin of subfigure in figure 
        sp_r = 0.95     # ratio for right margin of subfigure in figure 
        textwidth = _textwidth

    if mode == 'thesis_half':
        ### font sizes
        fs_big = 14          # size of big letters in pt
        fs_med = 12
        fs_small =10        # size of small letters pt
        ### subplot margins
        sp_t = 0.88     # ratio for top of subfigure in figure 
        sp_b = 0.20     # ratio for bottom of subfigure in figure 
        sp_l = 0.17     # ratio for left margin of subfigure in figure 
        sp_r = 0.96     # ratio for right margin of subfigure in figure 
        textwidth = _textwidth/2.

    if mode == 'ct_thesis':
        ### font sizes
        fs_big = 14          # size of big letters in pt
        fs_med = 12
        fs_small =10        # size of small letters pt
        ### subplot margins
        sp_t = 0.92     # ratio for top of subfigure in figure 
        sp_b = 0.00     # ratio for bottom of subfigure in figure 
        sp_l = 0.00     # ratio for left margin of subfigure in figure 
        sp_r = 1.00     # ratio for right margin of subfigure in figure 
        textwidth = _textwidth

    if mode == 'ct':
        ### font sizes
        fs_big = 14          # size of big letters in pt
        fs_med = 12
        fs_small =10        # size of small letters pt
        ### subplot margins
        sp_t = 0.99     # ratio for top of subfigure in figure 
        sp_b = 0.01     # ratio for bottom of subfigure in figure 
        sp_l = 0.01     # ratio for left margin of subfigure in figure 
        sp_r = 0.99     # ratio for right margin of subfigure in figure 
        textwidth = _textwidth

    ### define figure size
    golden_mean = (np.sqrt(5)-1.0)/2.0  # aesthetic ratio
    fig_width = sf*textwidth/_dpi           # figure width in inches
    fig_height =fig_width*golden_mean   # height in inches (golden mean)
    fig_size =  [fig_width,fig_height]      # size of figure
    ### write rcParameters for dynamic use
    ### see matplotlibrc for more info
    params = {'backend': 'pdf',             # set ending for saving figure
            'axes.titlesize': sf*fs_med,            # set title size
            'font.size': sf*fs_small,               # set standard font size
            'axes.linewidth': sf*0.68,               # set axis line width
            'axes.grid': False,                     # set grid
            'axes.formatter.limits': [-4, 4],   # use scientific notation if log10
                                                                # or if the axis range is smaller than the
                                                                # first or larger than the second           
            'font.family': 'sans-serif',            # set font family 
            #'sans-serif': ['Computer Modern Sans serif'],                   # use Computer Modern by default
            'axes.labelsize': sf*fs_med,        # set label size of axis
            'legend.fontsize': sf*fs_small, # set fontsize of legend
            'xtick.labelsize': sf*fs_small,     # set fontsize of xticks
            'ytick.labelsize': sf*fs_small,     # set fontsize of yticks
            'text.usetex': False,                   # decide whether to use tex compiler for font (e.g. axes ticks labeling)
            'mathtext.default': 'regular',    # set numbers and letters in math mode to sans-serif, use \mathrm{} for serif
            'figure.figsize': fig_size,             # set figure size
            'figure.dpi': _dpi,                     #set figure resolution
            'legend.fancybox': True,            # decide whether to use fancy/ordinary legend
            'lines.linewidth': sf*1.0,              # set line width
            'lines.markersize': sf*2,         # set marker size
            'xtick.major.size': sf*5,               # set size of major xticks
            'xtick.minor.size': sf*2,               # set size of minor xticks
            'ytick.major.size': sf*4,               # set size of major yticks
            'ytick.minor.size': sf*2,               # set size of minor yticks
            'xtick.major.pad': sf*4,                # distance to major tick label in points
            'xtick.minor.pad': sf*4,                # distance to minor tick label in points
            'ytick.major.pad': sf*4,                # distance to major tick label in points
            'ytick.minor.pad': sf*4,                # distance to minor tick label in points
            'grid.linewidth'   :   sf*0.3,          # set grid linewidth
            'figure.subplot.bottom': sp_b,  # set bottom position of subplot
            'figure.subplot.top': sp_t,         # set top position of subplot
            'figure.subplot.left': sp_l,            # set left margin of subplot
            'figure.subplot.right': sp_r}       # set right margin of subplot

    mpl.rcParams.update(params)     # update rc parameters
    return(params)


if __name__ == "__main__":
    ### EXAMPLE ### 

    load_defaults(3.0)

    ### create figure
    fig = plt.figure(1)
    ax = fig.add_subplot(111) 
    ### create array and plot it
    x,dx = np.linspace(0,10,100,retstep=True)   
    hist = ax.bar(x,np.sin(x),width=dx,align='center',alpha=0.7, label=r'$\mathrm{test \ histogram}$')
    func = ax.plot(x,np.sin(x),c='r',label=r'$\mathrm{test \ plot} \ \sin(x)$')
    ax.grid(True)
    ### set title and axes label
    plt.xlabel(r'$X$')
    plt.ylabel(r'$Y$')
    plt.title(r'$Testplot$')
    ### offset x and y axis label
    ax.axes.xaxis.set_label_coords(0.5, -0.08)
    ax.axes.yaxis.set_label_coords(-0.08, 0.5)
    ### plot legend and set transparency
    ax.leg = plt.legend(loc=0)
    ax.leg.get_frame().set_alpha(0.8)   
    plt.show()

