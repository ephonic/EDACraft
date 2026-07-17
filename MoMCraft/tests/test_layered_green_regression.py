import numpy as np

import mom._mom as M


def test_layered_cavity_green_regression():
    layers = [{"thickness": 4.5e-6, "eps_r": 3.9, "tand": 0.0}]
    dyad = M.build_dyadic_green_layered(
        8e9,
        layers,
        117.25e-6,
        117.25e-6,
        113.5e-6,
        118.0e-6,
        60,
        7,
    )

    ga_1 = dyad.vector_dot(1e-6, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    gp_1 = dyad.scalar_dot(1e-6, 1.0, 1.0)
    ga_mid = dyad.vector_dot(1e-5, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    gp_mid = dyad.scalar_dot(1e-5, 1.0, 1.0)
    ga_mid2 = dyad.vector_dot(5.1190583763642483e-5, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    gp_mid2 = dyad.scalar_dot(5.1190583763642483e-5, 1.0, 1.0)
    ga_2 = dyad.vector_dot(1e-4, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    gp_2 = dyad.scalar_dot(1e-4, 1.0, 1.0)

    # This cavity case is sensitive to the QWE tail/branch handling.
    # A past regression drove these values to a completely different scale
    # and collapsed the downstream port solve.
    assert np.isclose(ga_1.real, 1.266743355e5, rtol=5e-3)
    assert np.isclose(ga_1.imag, -4.19440253e1, rtol=5e-3)
    assert np.isclose(gp_1.real, 3.234250742e4, rtol=5e-3)
    assert np.isclose(gp_1.imag, -1.08036856e-2, rtol=5e-2)

    # The 10-50 um band is where the cavity-QWE branch split regressed before.
    assert np.isclose(ga_mid.real, 1.770948962e4, rtol=5e-3)
    assert np.isclose(ga_mid.imag, -7.34737721e0, rtol=5e-3)
    assert np.isclose(gp_mid.real, 2.864980790e3, rtol=5e-3)
    assert np.isclose(gp_mid.imag, 1.27449757e-4, rtol=5e-2)

    assert np.isclose(ga_mid2.real, 7.516332701e3, rtol=5e-3)
    assert np.isclose(ga_mid2.imag, -7.34544543e0, rtol=5e-3)
    assert np.isclose(gp_mid2.real, 2.544212667e2, rtol=5e-3)
    assert np.isclose(gp_mid2.imag, 1.27748330e-4, rtol=5e-2)

    assert np.isclose(ga_2.real, 6.308174010e3, rtol=5e-3)
    assert np.isclose(ga_2.imag, -7.339789861e0, rtol=5e-3)
    assert np.isclose(gp_2.real, -4.74222577e1, rtol=5e-3)
    assert np.isclose(gp_2.imag, 1.28622465e-4, rtol=5e-2)
