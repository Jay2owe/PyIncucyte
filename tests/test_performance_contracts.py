"""Exact numeric and ownership guards for calibration and catalogue speedups."""
import numpy as np
import pytest
import os
from pathlib import Path
import subprocess
import sys

from pyincucyte import engine, processing


def test_failed_settings_replace_preserves_previous_file(tmp_path, monkeypatch):
    from pyincucyte import _atomic
    target=tmp_path/'preset.json'
    target.write_text('{"previous": true}')
    def fail(*args):
        raise OSError('simulated replace failure')
    monkeypatch.setattr(_atomic.os,'replace',fail)
    with pytest.raises(OSError,match='replace failure'):
        _atomic.write_json(target,{'new':True})
    assert target.read_text()=='{"previous": true}'
    assert list(tmp_path.iterdir())==[target]


def test_offline_demo_entrypoint_preserves_frozen_answers(tmp_path):
    import hashlib
    root=Path(__file__).resolve().parents[1]
    expected=root/'demo/expected_result.json'
    before=hashlib.sha256(expected.read_bytes()).hexdigest()
    env=dict(os.environ,TEMP=str(tmp_path),TMP=str(tmp_path))
    done=subprocess.run([sys.executable,str(root/'demo/run_demo.py')],env=env,capture_output=True,text=True,check=True)
    assert '"verified": true' in done.stdout
    refused=subprocess.run([sys.executable,str(root/'demo/run_demo.py'),'--update-expected'],env=env,capture_output=True,text=True)
    assert refused.returncode==2 and '--reason' in refused.stderr
    assert hashlib.sha256(expected.read_bytes()).hexdigest()==before


def test_unpack_keeps_mixed_types_independent_containers_and_wrapper_errors():
    from pyincucyte.engine import unpack_values
    class Number(int):pass
    number=Number(3)
    original={'$type':'discard','Data':{'$values':[0,255,True,None,1.5,'text',number,{'$type':'discard','bytes':[1,2]}]}}
    result=unpack_values(original)
    assert result=={'Data':[0,255,True,None,1.5,'text',number,{'bytes':[1,2]}]}
    assert type(result['Data'][2]) is bool and result['Data'][6] is number
    result['Data'][7]['bytes'].append(9)
    assert original['Data']['$values'][7]['bytes']==[1,2]
    with pytest.raises(TypeError):unpack_values({'$values':None})


@pytest.mark.parametrize('length',[255,256,257])
def test_large_integer_payload_retains_copies_and_last_nested_record(length):
    from pyincucyte.engine import unpack_values
    values=list(range(length))
    decoded=unpack_values({'$values':values})
    assert decoded==values and decoded is not values
    decoded.append(-1)
    assert len(values)==length
    mixed=values+[{'$type':'strip','nested':{'$values':[True,None,4.]}}]
    assert unpack_values(mixed)==values+[{'nested':[True,None,4.]}]
    class CustomList(list):
        def copy(self):raise AssertionError('Custom copy is not the list contract')
    assert unpack_values(CustomList(values))==values


def test_preview_preparation_is_bounded_and_defers_work(monkeypatch):
    from pyincucyte.gui import preview
    started=[]
    class Worker:
        def __init__(self,**kwargs):self.kwargs=kwargs
        def start(self):started.append(self.kwargs)
    monkeypatch.setattr(preview,'_PREPARATION_STARTED',False)
    monkeypatch.setattr(preview.threading,'Thread',Worker)
    preview.prepare_preview();preview.prepare_preview()
    assert len(started)==1 and started[0]['daemon'] is True
    assert callable(started[0]['target'])


def test_tile_response_unwraps_nested_bytes_once_and_preserves_null_positions():
    from pyincucyte.pyramid import response_tiles,PyramidUnavailable
    payload={'Data':{'Tiles':{'$values':[{'Bytes':{'$values':[1,2,3]},'ImageWidth':3},None]}}}
    result=response_tiles(payload,2)
    assert result==[{'Bytes':[1,2,3],'ImageWidth':3},None]
    result[0]['Bytes'][0]=99
    assert payload['Data']['Tiles']['$values'][0]['Bytes']['$values'][0]==1
    with pytest.raises(PyramidUnavailable):response_tiles(payload,1)


def test_package_metadata_is_light_and_all_public_exports_resolve():
    import pyincucyte
    for name in pyincucyte.__all__:
        getattr(pyincucyte, name)  # Some public configuration defaults may be None.
        assert name in dir(pyincucyte)
    code = "import sys,pyincucyte; assert 'numpy' not in sys.modules; assert 'requests' not in sys.modules; assert 'tkinter' not in sys.modules; from pyincucyte import IncucyteClient; from pyincucyte.client import IncucyteClient as C; assert IncucyteClient is C; import incucyte_downloader; from pyincucyte import engine; assert incucyte_downloader is engine"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    subprocess.run([sys.executable,"-c",code],env=env,check=True,capture_output=True,text=True)


@pytest.mark.parametrize("dtype", [np.uint16, np.float32, np.float64])
@pytest.mark.parametrize("calibrate", [False, True])
def test_processing_preserves_input_and_original_operation_order(dtype, calibrate):
    data = np.arange(63, dtype=dtype).reshape(7, 9)[:, ::2]
    original = data.copy()
    plan = dict(scale=2.5, bias=3., calibrate=calibrate, background=5., unmix=[])
    expected = ((data.astype("float32")-3.)/2.5 if calibrate else data.astype("float32"))
    expected = expected - ((np.asarray(5., dtype="float32")-3.)/2.5 if calibrate else 5.)
    expected = np.clip(expected, 0, None)
    expected = expected.astype("float32" if calibrate else dtype)
    data.setflags(write=False)
    got = processing.apply(data, plan)
    np.testing.assert_array_equal(got, expected)
    np.testing.assert_array_equal(data, original)
    assert not np.shares_memory(got, data)


def test_catalogue_retains_first_tie_nested_fallback_and_independent_records():
    first = {"VesselID": 3, "Channels": {"x": [1]}}
    second = {"VesselID": 4, "Channels": {"x": [2]}}
    response = {"Data": {"SearchVessels": {"$values": [first]}, "Vessels": [second]}}
    result = engine.extract_search_vessels(response)
    assert result == [first]
    result[0]["Channels"]["x"].append(9)
    assert first["Channels"]["x"] == [1]
    assert engine.extract_search_vessels({"Data": {"nested": {"items": [second]}}}) == [second]
    assert engine.extract_search_vessels({"Data": {"$values": [first], "SearchVessels": [first, second]}}) == [first, second]


@pytest.mark.parametrize('calibrate',[False,True])
@pytest.mark.parametrize('value',[10,np.float32(10),np.asarray(10,dtype='float32')])
def test_processing_retains_scalar_result_type(value,calibrate):
    plan=dict(scale=2.3,bias=3.1,calibrate=calibrate,background=5.2,unmix=[])
    data=np.asarray(value,dtype='float32')
    expected=((data-3.1)/2.3 if calibrate else data)
    expected=expected-((np.asarray(5.2,dtype='float32')-3.1)/2.3 if calibrate else 5.2)
    expected=np.clip(expected,0,None).astype('float32' if calibrate else np.asarray(value).dtype)
    actual=processing.apply(value,plan)
    assert type(actual) is type(expected)
    np.testing.assert_array_equal(actual,expected)


def test_unmix_preserves_promoted_intermediate_precision():
    data=np.random.default_rng(14).uniform(1000,2000,(7,9)).astype('float32')
    ratios=[np.float64(.1234567891011),np.float64(.2323456789)]
    terms=[dict(contributor=3,scale=2.,bias=1.,background=3.,ratio=r,sigma=0.) for r in ratios]
    plan=dict(scale=2.3,bias=3.1,calibrate=True,background=5.2,unmix=terms)
    expected=(data-3.1)/2.3-(np.asarray(5.2,dtype='float32')-3.1)/2.3
    other=(data-1.)/2.-(np.asarray(3.,dtype='float32')-1.)/2.
    for ratio in ratios:expected=expected-ratio*other
    expected=np.clip(expected,0,None).astype('float32')
    np.testing.assert_array_equal(processing.apply(data,plan,lambda _:data),expected)


def test_calibration_preserves_numpy_promotion_for_large_coefficients():
    data=np.array([10.,20.],dtype='float32')
    with np.errstate(over='ignore',invalid='ignore'):
        expected=(data-float(-1e300))/float(1e300)
        actual=processing._calibrated(data,1e300,-1e300)
    assert actual.dtype==expected.dtype
    np.testing.assert_array_equal(actual,expected)


@pytest.mark.parametrize('calibrate',[False,True])
def test_processing_preserves_nonfinite_and_extreme_float_arithmetic(calibrate):
    data=np.array([[np.nan,np.inf,-np.inf],[np.finfo('float32').max,
                    np.finfo('float32').smallest_subnormal,-100.]],dtype='float32')
    saved=data.copy();data.setflags(write=False)
    plan=dict(scale=2.3,bias=3.1,calibrate=calibrate,background=5.2,
              unmix=[dict(contributor=3,scale=2.,bias=1.,background=3.,ratio=.12,sigma=0.)])
    with np.errstate(invalid='ignore',over='ignore'):
        expected=((data-3.1)/2.3 if calibrate else data.copy())
        expected=expected-((np.asarray(5.2,dtype='float32')-3.1)/2.3 if calibrate else 5.2)
        other=((data-1.)/2. if calibrate else data.copy())
        other=other-((np.asarray(3.,dtype='float32')-1.)/2. if calibrate else 3.)
        expected=np.clip(expected-.12*other,0,None).astype('float32')
        actual=processing.apply(data,plan,lambda _:data)
    np.testing.assert_array_equal(actual,expected)
    np.testing.assert_array_equal(data,saved)
