import numpy as np
import pandas as pd
import numpy.ma as ma
from scipy.optimize import curve_fit
import numpy.linalg as LA
import math
import struct
import sys

import diff_classifier.utils as ut
import diff_classifier.msd as msd


def unmask_track(track):
    """
    Removes empty frames from a track in an MSD pandas dataframe.

    Parameters
    ----------
    track : pandas Dataframe
        At a minimum, must contain a Frame, Track_ID, X, Y, MSDs, and
        Gauss column.

    Returns
    -------
    comp_track : pandas Dataframe
        Similar to track, but has all masked components removed.

    Examples
    --------

    """
    x = ma.masked_invalid(track['X'])
    msd = ma.masked_invalid(track['MSDs'])
    x_mask = ma.getmask(x)
    msd_mask = ma.getmask(msd)
    comp_frame = ma.compressed(ma.masked_where(msd_mask, track['Frame']))
    comp_ID = ma.compressed(ma.masked_where(msd_mask, track['Track_ID']))
    comp_x = ma.compressed(ma.masked_where(x_mask, track['X']))
    comp_y = ma.compressed(ma.masked_where(x_mask, track['Y']))
    comp_msd = ma.compressed(ma.masked_where(msd_mask, track['MSDs']))
    comp_gauss = ma.compressed(ma.masked_where(msd_mask, track['Gauss']))

    d = {'Frame': comp_frame,
         'Track_ID': comp_ID,
         'X': comp_x,
         'Y': comp_y,
         'MSDs': comp_msd,
         'Gauss': comp_gauss
         }
    comp_track = pd.DataFrame(data=d)
    return comp_track


def alpha_calc(track):
    """
    Calculates the parameter alpha by fitting track MSD data to a function.

    Parameters
    ----------
    track : pandas DataFrame
        At a minimum, must contain a Frames and a MSDs column.  The function
        msd_calc can be used to generate the correctly formatted pd dataframe.

    Returns
    -------
    a : numpy.float64
        The anomalous exponent derived by fitting MSD values to the function,
        <r**2(n)> = 4*D*(n*delt)**a
    D : numpy.float64
        The fitted diffusion coefficient derived by fitting MSD values to the
        function above.

    Examples
    --------
    >>> frames = 5
    >>> d = {'Frame': np.linspace(1, frames, frames),
             'X': np.linspace(1, frames, frames)+5,
             'Y': np.linspace(1, frames, frames)+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> alpha_calc(df)
    (2.0000000000000004, 0.4999999999999999)

    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
               'X': np.sin(np.linspace(1, frames, frames)+3),
               'Y': np.cos(np.linspace(1, frames, frames)+3)}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> alpha_calc(df)
    (0.023690002018364065, 0.5144436515510022)
    """

    # assert type(track) == pd.core.frame.DataFrame, "track must be a pandas dataframe."
    # assert type(track['MSDs']) == pd.core.series.Series, "track must contain MSDs column."
    # assert type(track['Frame']) == pd.core.series.Series, "track must contain Frame column."
    # assert track.shape[0] > 0, "track must not be empty."

    y = track['MSDs']
    x = track['Frame']

    def msd_alpha(x, a, D):
        return 4*D*(x**a)

    try:
        popt, pcov = curve_fit(msd_alpha, x, y)
        a = popt[0]
        D = popt[1]
    except RuntimeError:
        print('Optimal parameters not found. Print NaN instead.')
        a = np.nan
        D = np.nan
    return a, D


def gyration_tensor(track):
    """
    Calculates the eigenvalues and eigenvectors of the gyration tensor of the
    input trajectory.

    Parameters
    ----------
    track : pandas DataFrame
        At a minimum, must contain an X and Y column.  The function
        msd_calc can be used to generate the correctly formatted pd dataframe.

    Returns
    -------
    l1 : numpy.float64
        Dominant eigenvalue of the gyration tensor.
    l2 : numpy.float64
        Secondary eigenvalue of the gyration tensor.
    v1 : 2 x 1 numpy.ndarray of numpy.float64 objects
        Dominant eigenvector of the gyration tensor.
    v2 : 2 x 1 numpy.ndarray of numpy.float64 objects
        Secondary eigenvector of the gyration tensor.

    Examples
    --------
    >>> frames = 5
    >>> d = {'Frame': np.linspace(1, frames, frames),
             'X': np.linspace(1, frames, frames)+5,
             'Y': np.linspace(1, frames, frames)+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> gyration_tensor(df)
    (4.0,
    4.4408920985006262e-16,
    array([ 0.70710678, -0.70710678]),
    array([ 0.70710678,  0.70710678]))

    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
               'X': np.sin(np.linspace(1, frames, frames)+3),
               'Y': np.cos(np.linspace(1, frames, frames)+3)}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> gyration_tensor(df)
    (0.53232560128104522,
    0.42766829138901619,
    array([ 0.6020119 , -0.79848711]),
    array([-0.79848711, -0.6020119 ]))
    """

    df = track
    assert type(df) == pd.core.frame.DataFrame, "track must be a pandas dataframe."
    assert type(df['X']) == pd.core.series.Series, "track must contain X column."
    assert type(df['Y']) == pd.core.series.Series, "track must contain Y column."
    assert df.shape[0] > 0, "track must not be empty."

    Ta = np.sum((df['X'] - np.mean(df['X']))**2)/df['X'].shape[0]
    Tb = np.sum((df['Y'] - np.mean(df['Y']))**2)/df['Y'].shape[0]
    Tab = np.sum((df['X'] - np.mean(df['X']))*(df['Y'] - np.mean(df['Y'])))/df['X'].shape[0]

    w, v = LA.eig(np.array([[Ta, Tab], [Tab, Tb]]))
    dom = np.argmax(np.abs(w))
    rec = np.argmin(np.abs(w))
    l1 = w[dom]
    l2 = w[rec]
    v1 = v[dom]
    v2 = v[rec]
    return l1, l2, v1, v2


def kurtosis(track):
    """
    Calculates the kurtosis of input track.

    Parameters
    ----------
    track : pandas DataFrame
        At a minimum, must contain an X and Y column.  The function
        msd_calc can be used to generate the correctly formatted pd dataframe.

    Returns
    -------
    kurt : numpy.float64
        Kurtosis of the input track.  Calculation based on projected 2D positions
        on the dominant eigenvector of the radius of gyration tensor.

    Examples
    --------
    >>> frames = 5
    >>> d = {'Frame': np.linspace(1, frames, frames),
             'X': np.linspace(1, frames, frames)+5,
             'Y': np.linspace(1, frames, frames)+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> kurtosis(df)
    2.5147928994082829

    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
               'X': np.sin(np.linspace(1, frames, frames)+3),
               'Y': np.cos(np.linspace(1, frames, frames)+3)}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> kurtosis(df)
    1.8515139698652476
    """

    df = track
    assert type(df) == pd.core.frame.DataFrame, "track must be a pandas dataframe."
    assert type(df['X']) == pd.core.series.Series, "track must contain X column."
    assert type(df['Y']) == pd.core.series.Series, "track must contain Y column."
    assert df.shape[0] > 0, "track must not be empty."

    l1, l2, v1, v2 = gyration_tensor(df)
    projection = df['X']*v1[0] + df['Y']*v1[1]

    kurt = np.mean((projection - np.mean(projection))**4/(np.std(projection)**4))

    return kurt


def asymmetry(track):
    """
    Calculates the asymmetry of the trajectory.

    Parameters
    ----------
    track : pandas DataFrame
        At a minimum, must contain an X and Y column.  The function
        msd_calc can be used to generate the correctly formatted pd dataframe.

    Returns
    -------
    l1 : numpy.float64
        Dominant eigenvalue of the gyration tensor.
    l2 : numpy.float64
        Secondary eigenvalue of the gyration tensor.
    a1 : numpy.float64
        asymmetry of the input track.  Equal to 0 for circularly symmetric tracks,
        and 1 for linear tracks.
    a2 : numpy.float64
        alternate definition of asymmetry.  Equal to 1 for circularly
        symmetric tracks, and 0 for linear tracks.
    a3 : numpy.float64
        alternate definition of asymmetry.

    Examples
    --------
    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
             'X': np.linspace(1, frames, frames)+5,
             'Y': np.linspace(1, frames, frames)+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> asymmetry(df)
    (16.5, 0.0, 1.0, 0.0, 0.69314718055994529)

    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
               'X': np.sin(np.linspace(1, frames, frames)+3),
               'Y': np.cos(np.linspace(1, frames, frames)+3)}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> asymmetry(df)
    (0.53232560128104522,
    0.42766829138901619,
    0.046430119259539708,
    0.80339606128247354,
    0.0059602683290953052)
    """

    assert type(track) == pd.core.frame.DataFrame, "track must be a pandas dataframe."
    assert type(track['X']) == pd.core.series.Series, "track must contain X column."
    assert type(track['Y']) == pd.core.series.Series, "track must contain Y column."
    assert track.shape[0] > 0, "track must not be empty."

    l1, l2, v1, v2 = gyration_tensor(track)
    a1 = (l1**2 - l2**2)**2/(l1**2 + l2**2)**2
    a2 = l2/l1
    a3 = -np.log(1-((l1-l2)**2)/(2*(l1+l2)**2))

    return l1, l2, a1, a2, a3


def minBoundingRect(df):
    """
    Calculates the minimum bounding rectangle of an input trajectory.

    Parameters
    ----------
    df : pandas DataFrame
        At a minimum, must contain an X and Y column.  The function
        msd_calc can be used to generate the correctly formatted pd dataframe.

    Returns
    -------
    rot_angle : numpy.float64
        Angle of rotation of the bounding box.
    area : numpy.float64
        Area of the bounding box.
    width : numpy.float64
        Width of the bounding box.
    height : numpy.float64
        Height of the bounding box.
    center_point : 2 x 1 numpy.ndarray of numpy.float64 objects
        Center point of the bounding box.
    corner_points : 4 x 2 numpy.ndarray of numpy.float64 objects
        Corner points of the bounding box.

    Examples
    --------
    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
             'X': np.linspace(1, frames, frames)+5,
             'Y': np.linspace(1, frames, frames)+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> minBoundingRect(df)
    (-2.3561944901923448,
    2.8261664256307952e-14,
    12.727922061357855,
    2.2204460492503131e-15,
    array([ 10.5,   8.5]),
    array([[  6.,   4.],
           [ 15.,  13.],
           [ 15.,  13.],
           [  6.,   4.]]))

    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
               'X': np.sin(np.linspace(1, frames, frames))+3,
               'Y': np.cos(np.linspace(1, frames, frames))+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> minBoundingRect(df)
    (0.78318530717958657,
    3.6189901131223992,
    1.9949899732081091,
    1.8140392491811692,
    array([ 3.02076903,  2.97913884]),
    array([[ 4.3676025 ,  3.04013439],
           [ 2.95381341,  1.63258851],
           [ 1.67393557,  2.9181433 ],
           [ 3.08772466,  4.32568917]]))

    Notes
    -----
    Based off of code from the following repo:
    https://github.com/dbworth/minimum-area-bounding-rectangle/blob/master/python/min_bounding_rect.py
    """

    assert type(df) == pd.core.frame.DataFrame, "track must be a pandas dataframe."
    assert type(df['X']) == pd.core.series.Series, "track must contain X column."
    assert type(df['Y']) == pd.core.series.Series, "track must contain Y column."
    assert df.shape[0] > 0, "track must not be empty."

    df2 = np.zeros((df.shape[0]+1, 2))
    df2[:-1, :] = df[['X', 'Y']].values
    df2[-1, :] = df[['X', 'Y']].values[0, :]
    hull_points_2d = df2

    edges = np.zeros((len(hull_points_2d)-1, 2))

    for i in range(len(edges)):
        edge_x = hull_points_2d[i+1, 0] - hull_points_2d[i, 0]
        edge_y = hull_points_2d[i+1, 1] - hull_points_2d[i, 1]
        edges[i] = [edge_x, edge_y]

    edge_angles = np.zeros((len(edges)))

    for i in range(len(edge_angles)):
        edge_angles[i] = math.atan2(edges[i, 1], edges[i, 0])
    edge_angles = np.unique(edge_angles)

    start_area = platform_c_maxint = 2 ** (struct.Struct('i').size * 8 - 1) - 1
    min_bbox = (0, start_area, 0, 0, 0, 0, 0, 0)
    for i in range(len(edge_angles)):
        R = np.array([[math.cos(edge_angles[i]), math.cos(edge_angles[i]-(math.pi/2))],
                     [math.cos(edge_angles[i]+(math.pi/2)), math.cos(edge_angles[i])]])

        rot_points = np.dot(R, np.transpose(hull_points_2d))

        min_x = np.nanmin(rot_points[0], axis=0)
        max_x = np.nanmax(rot_points[0], axis=0)
        min_y = np.nanmin(rot_points[1], axis=0)
        max_y = np.nanmax(rot_points[1], axis=0)

        width = max_x - min_x
        height = max_y - min_y
        area = width*height

        if (area < min_bbox[1]):
            min_bbox = (edge_angles[i], area, width, height, min_x, max_x, min_y, max_y)

    angle = min_bbox[0]
    R = np.array([[math.cos(angle), math.cos(angle-(math.pi/2))], [math.cos(angle+(math.pi/2)), math.cos(angle)]])
    proj_points = np.dot(R, np.transpose(hull_points_2d))

    min_x = min_bbox[4]
    max_x = min_bbox[5]
    min_y = min_bbox[6]
    max_y = min_bbox[7]

    center_x = (min_x + max_x)/2
    center_y = (min_y + max_y)/2
    center_point = np.dot([center_x, center_y], R)

    corner_points = np.zeros((4, 2))
    corner_points[0] = np.dot([max_x, min_y], R)
    corner_points[1] = np.dot([min_x, min_y], R)
    corner_points[2] = np.dot([min_x, max_y], R)
    corner_points[3] = np.dot([max_x, max_y], R)

    return (angle, min_bbox[1], min_bbox[2], min_bbox[3], center_point, corner_points)


def aspectratio(track):
    """
    Calculates the aspect ratio of the rectangle containing the input track.

    Parameters
    ----------
    track : pandas DataFrame
        At a minimum, must contain an X and Y column.  The function
        msd_calc can be used to generate the correctly formatted pd dataframe.

    Returns
    -------
    ar : numpy.float64
        aspect ratio of the trajectory.  Always >= 1.
    elong : numpy.float64
        elongation of the trajectory.  A transformation of the aspect ratio given
        by 1 - ar**-1.

    Examples
    --------
    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
             'X': np.linspace(1, frames, frames)+5,
             'Y': np.linspace(1, frames, frames)+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> aspectratio(df)
    (5732146505273195.0, 0.99999999999999978)

    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
               'X': np.sin(np.linspace(1, frames, frames))+3,
               'Y': np.cos(np.linspace(1, frames, frames))+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> aspectratio(df)
    (1.0997501702946164, 0.090702573174318291)

    """

    assert type(track) == pd.core.frame.DataFrame, "track must be a pandas dataframe."
    assert type(track['X']) == pd.core.series.Series, "track must contain X column."
    assert type(track['Y']) == pd.core.series.Series, "track must contain Y column."
    assert track.shape[0] > 0, "track must not be empty."

    rot_angle, area, width, height, center_point, corner_points = minBoundingRect(track)
    ar = width/height
    if ar > 1:
        counter = 1
    else:
        ar = 1/ar
    elong = 1 - (1/ar)

    return ar, elong, center_point


def boundedness(track, framerate=1):
    """
    Calculates the boundedness, fractal dimension, and trappedness of the input track.

    Parameters
    ----------
    track : pandas DataFrame
        At a minimum, must contain a Frames and a MSDs column.  The function
        msd_calc can be used to generate the correctly formatted pd dataframe.
    framerate : framrate of the video being analyzed.  Actually cancels out. So
        why did I include this. Default is 1.

    Returns
    -------
    B : numpy.float64
        Boundedness of the input track.  Quantifies how much a particle with
        diffusion coefficient D is restricted by a circular confinement of radius
        r when it diffuses for a time duration N*delt.  Defined as B = D*N*delt/r**2.
        For this case, D is the short time diffusion coefficient (after 2 frames),
        and r is half the maximum distance between any two positions.
    Df : numpy.float64
        The fractal path dimension defined as Df = log(N)/log(N*d*l**-1) where L
        is the total length (sum over all steplengths), N is the number of steps,
        and d is the largest distance between any two positions.
    pf : numpy.float64
        The probability that a particle with diffusion coefficient D and traced
        for a period of time N*delt is trapped in region r0.  Given by
        pt = 1 - exp(0.2048 - 0.25117*(D*N*delt/r0**2))
        For this case, D is the short time diffusion coefficient, and r0 is half
        the maximum distance between any two positions.

    Examples
    --------
    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
             'X': np.linspace(1, frames, frames)+5,
             'Y': np.linspace(1, frames, frames)+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> boundedness(df)
    (1.0, 1.0000000000000002, 0.045311337970735499)

    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
               'X': np.sin(np.linspace(1, frames, frames)+3),
               'Y': np.cos(np.linspace(1, frames, frames)+3)}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> boundedness(df)
    (0.96037058689895005, 2.9989749477908401, 0.03576118370932313)
    """

    assert type(track) == pd.core.frame.DataFrame, "track must be a pandas dataframe."
    assert type(track['MSDs']) == pd.core.series.Series, "track must contain MSDs column."
    assert type(track['Frame']) == pd.core.series.Series, "track must contain Frame column."
    assert track.shape[0] > 0, "track must not be empty."

    df = track

    if df.shape[0] > 2:
        length = df.shape[0]
        distance = np.zeros((length, length))

        for frame in range(0, length-1):
            distance[frame, 0:length-frame-1] = (np.sqrt(msd.nth_diff(df['X'], frame+1)**2 + msd.nth_diff(df['Y'], frame+1)**2).values)

        L = np.sum((np.sqrt(msd.nth_diff(df['X'], 1)**2 + msd.nth_diff(df['Y'], 1)**2).values))
        r = np.max(distance)/2
        N = df['Frame'][df['Frame'].shape[0]-1]
        f = N*framerate
        D = df['MSDs'][2]/(4*f)

        B = D*f/(r**2)
        Df = np.log(N)/np.log(N*2*r/L)
        pf = 1 - np.exp(0.2048 - 0.25117*(D*f/(r**2)))
    else:
        B = np.nan
        Df = np.nan
        pf = np.nan

    return B, Df, pf


def efficiency(track):
    """
    Calculates the efficiency and straitness of the input track

    Parameters
    ----------
    track : pandas DataFrame
        At a minimum, must contain a Frames and a MSDs column.  The function
        msd_calc can be used to generate the correctly formatted pd dataframe.

    Returns
    -------
    eff : numpy.float64
        Efficiency of the input track.  Relates the sum of squared step
        lengths.  Based on Helmuth et al. (2007) and defined as:
        E = |x(N-1)-x(0)|**2/SUM(|x(i) - x(i-1)|**2
    strait : numpy.float64
        Relates the net displacement L to teh sum of step lengths and is
        defined as:
        S = |x(N-1)-x(0)|/SUM(|x(i) - x(i-1)|

    Examples
    --------
    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
                   'X': np.linspace(1, frames, frames)+5,
                   'Y': np.linspace(1, frames, frames)+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> ft.efficiency(df)
    (9.0, 0.9999999999999999)

    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
                   'X': np.sin(np.linspace(1, frames, frames))+3,
                   'Y': np.cos(np.linspace(1, frames, frames))+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> ft.efficiency(df)
    (0.46192924086141945, 0.22655125514290225)
    """

    df = track
    length = df.shape[0]
    num = (msd.nth_diff(df['X'], length-1)**2 + msd.nth_diff(df['Y'], length-1)**2)[0]
    num2 = np.sqrt(num)

    den = np.sum(msd.nth_diff(df['X'], 1)**2 + msd.nth_diff(df['Y'], 1)**2)
    den2 = np.sum(np.sqrt(msd.nth_diff(df['X'], 1)**2 + msd.nth_diff(df['Y'], 1)**2))

    eff = num/den
    strait = num2/den2
    return eff, strait


def msd_ratio(track, n1=3, n2=100):
    """
    Calculates the MSD ratio of the input track at the specified frames.

    Parameters
    ----------
    track : pandas DataFrame
        At a minimum, must contain a Frames and a MSDs column.  The function
        msd_calc can be used to generate the correctly formatted pd dataframe.
    n1 : int
        First frame at which to calculate the MSD ratio.
    n2 : int
        Last frame at which to calculate the MSD ratio.

    Returns
    -------
    ratio: numpy.float64
        MSD ratio as defined by
        [MSD(n1)/MSD(n2)] - [n1/n2]
        where n1 < n2.  For Brownian motion, it is 0; for restricted motion it
        is < 0.  For directed motion it is > 0.

    Examples
    --------
    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
             'X': np.linspace(1, frames, frames)+5,
             'Y': np.linspace(1, frames, frames)+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> ft.msd_ratio(df, 1, 9)
    -0.18765432098765433

    >>> frames = 10
    >>> d = {'Frame': np.linspace(1, frames, frames),
             'X': np.sin(np.linspace(1, frames, frames))+3,
             'Y': np.cos(np.linspace(1, frames, frames))+3}
    >>> df = pd.DataFrame(data=d)
    >>> df['MSDs'], df['Gauss'] = msd_calc(df)
    >>> ft.msd_ratio(df, 1, 9)
    0.04053708075268797
    """

    df = track
    assert n1 < n2, "n1 must be less than n2"
    ratio = (df['MSDs'][n1]/df['MSDs'][n2]) - (df['Frame'][n1]/df['Frame'][n2])
    return ratio


def calculate_features(df, framerate=1):
    """
    Calculates multiple features from input MSD dataset and stores in pandas dataframe.

    Parameters
    ----------
    df : pandas dataframe
        Output from msd.all_msds2.  Must have at a minimum the following columns:
        Track_ID, Frame, X, Y, and MSDs.
    framerate : int or float64
        Framerate of the input videos from which trajectories were calculated.  Required
        for accurate calculation of some features.  Default is 1.  Possibly not required.
        Ignore if performing all calcuations without units.

    Returns
    -------
    di: pandas dataframe
        Contains a row for each trajectory in df.  Holds the following features of each
        trajetory: Track_ID, alpha, D_fit, kurtosis, asymmetry1, asymmetry2, asymmetry3,
        aspect ratio (AR), elongation, boundedness, fractal dimension (fractal_dim),
        trappedness, efficiency, straightness, MSD ratio, frames, X, and Y.

    Examples
    --------
    See example outputs from individual feature functions.
    """
    # Skeleton of Trajectory features metadata table.
    # Builds entry for each unique Track ID.
    holder = df.Track_ID.unique().astype(float)
    die = {'Track_ID': holder,
           'alpha': holder,
           'D_fit': holder,
           'kurtosis': holder,
           'asymmetry1': holder,
           'asymmetry2': holder,
           'asymmetry3': holder,
           'AR': holder,
           'elongation': holder,
           'boundedness': holder,
           'fractal_dim': holder,
           'trappedness': holder,
           'efficiency': holder,
           'straightness': holder,
           'MSD_ratio': holder,
           'frames': holder,
           'X': holder,
           'Y': holder}

    di = pd.DataFrame(data=die)

    trackids = df.Track_ID.unique()
    partcount = trackids.shape[0]

    for particle in range(0, partcount):
        single_track_masked = df.loc[df['Track_ID'] == trackids[particle]].sort_values(['Track_ID', 'Frame'],
                                     ascending=[1, 1]).reset_index(drop=True)
        single_track = unmask_track(single_track_masked)
        di['alpha'][particle], di['D_fit'][particle] = alpha_calc(single_track)
        di['kurtosis'][particle] = kurtosis(single_track)
        l1, l2, di['asymmetry1'][particle], di['asymmetry2'][particle], di['asymmetry3'][particle] = asymmetry(single_track)
        di['AR'][particle], di['elongation'][particle], (di['X'][particle], di['Y'][particle]) = aspectratio(single_track)
        di['boundedness'][particle], di['fractal_dim'][particle], di['trappedness'][particle] = boundedness(single_track, framerate)
        di['efficiency'][particle], di['straightness'][particle] = efficiency(single_track)
        di['frames'][particle] = single_track.shape[0]
        if single_track['Frame'][single_track.shape[0]-2] > 2:
            di['MSD_ratio'][particle] = msd_ratio(single_track, 2, single_track['Frame'][single_track.shape[0]-2])
        else:
            di['MSD_ratio'][particle] = 0

    return di
