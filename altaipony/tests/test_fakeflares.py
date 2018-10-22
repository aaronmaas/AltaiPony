import pytest
import numpy as np
from inspect import signature

from ..fakeflares import inject_fake_flares, aflare, generate_fake_flare_distribution

from .test_flarelc import mock_flc

def test_merge_fake_and_recovered_events():
    pass

def test_generate_fake_flare_distribution():

    n = 500

    dur, ampl = generate_fake_flare_distribution(n)
    assert (dur <= 20).all()
    assert (dur >= 1e-4).all()
    assert (ampl <= 1e3).all()
    assert (ampl >= 1e-4).all()
    assert len(dur) == n
    assert len(ampl) == n

    dur, ampl = generate_fake_flare_distribution(n, mode='uniform')
    assert (dur <= 2e3/60/24).all()
    assert (dur >= 0.5/60/24).all()
    assert (ampl <= 1e3).all()
    assert (ampl >= 1e-4).all()
    assert len(dur) == n
    assert len(ampl) == n

def test_inject_fake_flares():
    flc = mock_flc(detrended=True)
    np.random.seed(84712)
    flc = flc.find_gaps()
    fake_flc = inject_fake_flares(flc)

    assert fake_flc.fake_flares.size == 20
    assert fake_flc.fake_flares.columns.values.tolist() == ['amplitude', 'duration_d',
                                                            'ed_inj', 'peak_time']
    assert fake_flc.detrended_flux_err.all() >= 1e-10
    assert fake_flc.detrended_flux.all() <= 1.
    assert fake_flc.detrended_flux.shape == flc.detrended_flux.shape
    print(fake_flc.fake_flares)
    flc = mock_flc(detrended=False)
    np.random.seed(84712)
    flc = flc.find_gaps()
    fake_flc = inject_fake_flares(flc, inject_before_detrending=True)

    assert fake_flc.fake_flares.size == 20
    assert fake_flc.fake_flares.columns.values.tolist() == ['amplitude', 'duration_d',
                                                            'ed_inj', 'peak_time']
    assert fake_flc.flux_err.all() >= 1e-10
    assert fake_flc.flux.all() <= 1.
    assert fake_flc.flux.shape == flc.flux.shape

def test_aflare_and_equivalent_duration():
    
    n = 1000
    time = np.arange(0, n/48, 1./48.)
    fl_flux = aflare(time, 11.400134, 1.415039, 110.981950)
    x = time * 60.0 * 60.0 * 24.0
    integral = np.sum(np.diff(x) * fl_flux[:-1])
    assert integral == pytest.approx(1.22e7,rel=1e-2)

    fl_flux = aflare(time, 11.400134, 1.415039, 110.981950, upsample=True)
    x = time * 60.0 * 60.0 * 24.0
    integral = np.sum(np.diff(x) * fl_flux[:-1])
    assert integral == pytest.approx(1.22e7,rel=1e-2)