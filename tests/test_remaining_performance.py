"""Strict JSON semantics remain unchanged by builtin fast paths."""
from datetime import date
from pathlib import Path
import json
import numpy as np
import pytest
from pyincucyte.models import json_clean
from pyincucyte.timeline import downsample_native


def test_json_subclasses_and_independent_containers():
    class CustomInt(int):
        def __int__(self):return 17
    class CustomFloat(float):
        def __float__(self):return 2.75
    class CustomDict(dict):
        def to_dict(self):return {'custom':True}
    original={'nested':[1,float('inf'),float('nan'),-0.0,np.int64(9),np.float32(1.5),
                        CustomInt(1),CustomFloat(1),CustomDict(ignored=1),Path('a'),date(2026,1,2)]}
    result=json_clean(original)
    assert result=={'nested':[1,None,None,-0.0,9,1.5,17,2.75,{'custom':True},'a','2026-01-02']}
    assert '-0.0' in json.dumps(result,allow_nan=False)
    result['nested'].append('changed')
    assert len(original['nested'])==11


@pytest.mark.parametrize('shape,edge', [((511,513),200),((256,256),1),((257,257),1)])
@pytest.mark.parametrize('dtype',['uint16','>u2','int16','float32','float64'])
def test_native_preview_partial_blocks_and_overflow_boundary(shape,edge,dtype):
    array=np.full(shape,65535 if 'u' in dtype else 12345,dtype=dtype)[:,::-1]
    array.flags.writeable=False
    factor=max(1,(max(shape)+edge-1)//edge)
    rows=np.arange(0,shape[0],factor);cols=np.arange(0,shape[1],factor)
    summed=np.add.reduceat(np.add.reduceat(array.astype('float64'),rows,axis=0),cols,axis=1)
    expected=summed/(np.minimum(factor,shape[0]-rows)[:,None]*np.minimum(factor,shape[1]-cols)[None,:])
    if np.issubdtype(array.dtype,np.integer):expected=np.rint(expected)
    result=downsample_native(array,max_edge=edge)
    np.testing.assert_array_equal(result,expected.astype(array.dtype))
    assert result.dtype==array.dtype and not np.shares_memory(result,array)


def original_blur(array,sigma):
    """Frozen pre-optimization arithmetic, including edge and no-op behavior."""
    sigma=float(sigma)
    if sigma<=0:return array
    data=np.asarray(array,dtype='float32')
    radius=max(1,int(round(3.*sigma)))
    offsets=np.arange(-radius,radius+1,dtype='float32')
    kernel=np.exp(-(offsets**2)/(2.*sigma*sigma));kernel/=kernel.sum()
    for axis in (0,1):
        pad=[(0,0),(0,0)];pad[axis]=(radius,radius)
        padded=np.pad(data,pad,mode='edge');blurred=np.zeros_like(data)
        for index,weight in enumerate(kernel):
            window=[slice(None),slice(None)];window[axis]=slice(index,index+data.shape[axis])
            blurred+=weight*padded[tuple(window)]
        data=blurred
    return data


@pytest.mark.parametrize('dtype',['uint16','>u2','int16','float32','float64'])
@pytest.mark.parametrize('layout',['contiguous','reversed','fortran','readonly'])
@pytest.mark.parametrize('sigma',[.1,1.5,4.])
def test_blur_reused_buffer_preserves_exact_arithmetic(dtype,layout,sigma):
    from pyincucyte.processing import _blur
    data=np.random.default_rng(20261014).integers(0,30000,(9,17)).astype(dtype)
    if layout=='reversed':data=data[::-1,::2]
    if layout=='fortran':data=np.asfortranarray(data)
    if layout=='readonly':data.flags.writeable=False
    before=data.copy();result=_blur(data,sigma)
    expected=original_blur(data,sigma)
    np.testing.assert_array_equal(result,expected)
    assert result.dtype==expected.dtype and not np.shares_memory(result,data)
    np.testing.assert_array_equal(data,before)


def test_blur_nonfinite_single_pixel_and_noop():
    from pyincucyte.processing import _blur
    for data in (np.array([[7]],dtype='float32'),np.array([[np.nan,np.inf,-np.inf,-0.0]],dtype='float32')):
        for sigma in (-1.,0.):assert _blur(data,sigma) is data
        with np.errstate(invalid='ignore'):
            np.testing.assert_array_equal(_blur(data,1.5),original_blur(data,1.5))
