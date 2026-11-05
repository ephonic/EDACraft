"""Explicit carrier temperatures at fixed three-temperature particle contacts.

CarrierReservoir.temperature_K remains the contact lattice temperature used
by band-edge and mobility laws. Omitted carrier values inherit that temperature.
This configuration does not convert statistics or calibrate a contact model.
"""
import numpy as np


def normalize_contact_temperatures(contacts, values):
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValueError('contact carrier temperatures must map faces to (electron,hole) K')
    result = {}
    for face, pair in values.items():
        if isinstance(face, (bool, np.bool_)) or not isinstance(face, (int, np.integer)) or face not in contacts:
            raise ValueError('carrier temperatures require an existing particle contact face')
        a = np.asarray(pair)
        if (a.shape != (2,) or a.dtype.kind not in 'iuf' or
            any(isinstance(v, (bool, np.bool_)) for v in pair) or
            np.any(~np.isfinite(a)) or np.any(a <= 1) or np.any(a >= 1e5)):
            raise ValueError('two finite real carrier contact temperatures strictly between 1 and 100000 K required')
        result[int(face)] = tuple(float(v) for v in a)
    return result


def carrier_contact_temperature(model, face, label):
    values = normalize_contact_temperatures(model.contacts, model.contact_carrier_temperature_K)
    if label not in ('electrons', 'holes'):
        raise ValueError('electron or hole contact temperature required')
    return values.get(face, (model.contacts[face].temperature_K,)*2)[label == 'holes']
