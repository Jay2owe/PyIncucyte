"""Frozen external Gaussian controls; no optional reference package at test time."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
from pyincucyte.processing import _blur

@pytest.mark.parametrize('sigma',[0.5,1.5,4.])
def test_smoothing_matches_independent_frozen_references(sigma):
    home=Path(__file__).resolve().parents[1]/'docs/software-performance'
    receipt=json.loads((home/'independent-images.json').read_text())
    packet=home/'independent-image-arrays.npz'
    assert hashlib.sha256(packet.read_bytes()).hexdigest()==receipt['arrays_sha256']
    prefix='sigma_'+str(sigma)
    with np.load(packet) as arrays:
        actual=_blur(arrays[prefix+'_input'],sigma)
        for reference in ('SciPy','OpenCV'):
            row=next(r for r in receipt['rows'] if r['case']==prefix and r['reference'].startswith(reference) and r['status']=='within_roundoff_bound')
            error=np.max(np.abs(actual.astype(float)-arrays[prefix+'_'+reference].astype(float)))
            assert error<=row['tolerance']
