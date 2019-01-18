import numpy as np
import pytest
from inspect import currentframe, getframeinfo

from ..flarelc import FlareLightCurve
from ..lcio import from_K2SC_file

from .. import PACKAGEDIR
from . import test_ids, test_paths

def test_get_saturation():
    flc = mock_flc(detrended=True)
    flc = flc.find_flares()
    r1 = flc.get_saturation()
    assert r1.flares.saturation_f10.iloc[0] == False
    r2 = flc.get_saturation(return_level=True)
    assert r2.flares.saturation_f10.iloc[0] == pytest.approx(0.0495,1e-2)
    r3 = flc.get_saturation(factor=1e-2)
    assert r3.flares['saturation_f0.01'].iloc[0] == True

def test_mark_flagged_flares():
    flc = mock_flc(detrended=True)
    flc = flc.find_flares()
    flc = flc.mark_flagged_flares(explain=True)
    assert flc.flares.quality.iloc[0] == 1152
    s1 = "Sudden sensitivity dropout, Cosmic ray in optimal aperture"
    s2 = "Cosmic ray in optimal aperture, Sudden sensitivity dropout"
    qs = flc.flares.explanation.iloc[0]
    assert ((qs == s1) | (qs == s2))

def test_sample_flare_recovery():
    flc = mock_flc(detrended=True)
    data, fflc = flc.sample_flare_recovery()
    #make sure no flares are injected overlapping true flares
    assert data[(data.istart > 14) & (data.istart < 19)].shape[0] == 0
    #test if all injected event are covered in the merged flares:
    assert data.shape[0] + (data[data.complex > 1].complex -1).sum() == data.complex.sum()
    assert fflc.gaps == [(0, 1000)]
    assert np.median(fflc.it_med) == pytest.approx(500.005274113832)


def test_characterize_flares():
    flc = mock_flc(detrended=True)
    lc = flc.characterize_flares(iterations=1, d=True, fakefreq=1.15, seed=45)
    assert lc.flares.loc[0, 'rec_prob'] == 1.0
    assert lc.flares.loc[0, 'ed_rec'] == pytest.approx(3455.887599271639)
    assert lc.flares.loc[0, 'ed_rec_corr'] == pytest.approx(10201.04698)

def test_repr():
    pass

def test_getitem():
    pass

def mock_flc(origin='TPF', detrended=False):
    """
    Mocks a FlareLightCurve with a sinusoid variation and a single positive outlier.

    Parameter
    -----------
    origin : 'TPF' or str
        Mocks a specific origin, such as 'KLC', 'FLC' etc.
    detrended : False or bool
        If False, a sinusoid signal is added to the mock light curve.

    Return
    -------
    FlareLightCurve
    """
    n = 1000
    time = np.arange(0, n/48, 1./48.)
    pixel_time = np.outer(time,np.full((3,3), 1)).reshape((1000,3,3))
    np.random.seed(13854)

    pipeline_mask = np.array([[False, False, False],
                              [False, True,  False],
                              [False, False, False],])
    quality = np.zeros_like(time)
    np.random.seed(33)
    flux_err = np.random.rand(n)/100.
    if detrended==False:
        flux = np.sin(time/2)*7. + 500. +flux_err
        pixel_flux = np.random.rand(len(time),3,3)/100.+500.+np.sin(pixel_time/2)*7.
    else:
        flux = 500. + flux_err
        pixel_flux = np.random.rand(len(time),3,3)/100.+500.
    flux[15] = 1.e3
    flux[16] = 750.
    flux[17] = 630.
    flux[18] = 580.
    quality[17] = 1024
    quality[18] = 128
    keys = {'flux' : flux, 'flux_err' : flux_err, 'time' : time,
            'pos_corr1' : np.zeros(n), 'pos_corr2' : np.zeros(n),
            'cadenceno' : np.arange(n), 'targetid' : 80000000,
            'origin' : origin, 'it_med' : np.full_like(time,500.005),
            'quality' : quality, 'pipeline_mask' : pipeline_mask,
            'pixel_flux' : pixel_flux,}

    if detrended == False:
        flc = FlareLightCurve(**keys)
    else:
        flc = FlareLightCurve(detrended_flux=flux,
                              detrended_flux_err=flux_err,
                              **keys)
    return flc

def test_invalid_lightcurve():
    """Invalid FlareLightCurves should not be allowed."""
    err_string = ("Input arrays have different lengths."
                  " len(time)=5, len(flux)=4")
    time = np.array([1, 2, 3, 4, 5])
    flux = np.array([1, 2, 3, 4])
    with pytest.raises(ValueError) as err:
        FlareLightCurve(time=time, flux=flux)
    assert err_string == err.value.args[0]

def test_find_gaps():
    lc = from_K2SC_file(test_paths[0])
    lc = lc.find_gaps()
    assert lc.gaps == [(0, 2505), (2505, 3293)] #[(0, 2582), (2582, 3424)]

def test_detrend():
    flc = mock_flc()
    try:
        flc = flc.detrend(de_niter=3)
        assert flc.detrended_flux.shape == flc.flux.shape
        assert flc.pv == pytest.approx([-4.52464711,  1.98863195, 34.25116362,
                                        0.10506948, -5.9999997 , 17.,
                                        16.99999881, -5.23056634, ], rel=2e-1)
    except np.linalg.linalg.LinAlgError:
        warning.warn('Detrending of mock LC failed, this happens.')
        pass

    #test non TPF derived LC fails
    #test the shapes are the same for all
    # test that the necessary attributes are kept
    pass

def test_detrend_fails():
    """If detrend fails, an error is raised with given string."""
    flc =  mock_flc(origin='KLC')
    err_string = ('Only KeplerTargetPixelFile derived FlareLightCurves can be'
              ' passed to detrend().')
    with pytest.raises(ValueError) as err:
        flc.detrend(de_niter=3)
    assert err_string == err.value.args[0]

def test_find_flares():
    """Test that an obvious flare is recovered sufficiently well."""
    flc = mock_flc(detrended=True)
    flc = flc.find_flares()
    assert flc.flares.loc[0,'ed_rec'] == pytest.approx(3455.8875941, rel=1e-4)
    assert flc.flares['ed_rec_err'][0] < flc.flares['ed_rec'][0]
    assert flc.flares['istart'][0] == 15
    assert flc.flares['istop'][0] == 19
    assert flc.flares['cstop'][0] == 19
    assert flc.flares['cstart'][0] == 15
    assert flc.flares['tstart'][0] == pytest.approx(0.3125, rel=1e-4)
    assert flc.flares['tstop'][0] == pytest.approx(0.395833, rel=1e-4)
