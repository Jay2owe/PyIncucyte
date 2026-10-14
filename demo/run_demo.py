"""Download and verify a tiny simulated acquisition without an instrument."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]


def run(directory, show=False, update_reason=None):
    os.environ["PYINCUCYTE_HOME"] = str(directory / "settings")
    import numpy as np
    import tifffile
    from pyincucyte import IncucyteClient
    from fakes import FakeDevice, logged_in_store, patched
    with patched(FakeDevice()), IncucyteClient("10.0.0.1", store=logged_in_store(directory)) as client:
        result = client.fetch(vessel=38, output=str(directory / "output"), wells="A1",
                              channels="phase,green", layout="time_channel_stack",
                              start_from="2026-03-01", end_at="2026-03-01")
        assert result.files, result.summary()
        pixels = tifffile.imread(result.files[0].path).reshape(2, 2, 6, 8)
        expected_path = Path(__file__).with_name("expected_result.json")
        expected = json.loads(expected_path.read_text())
        if update_reason:
            from datetime import datetime, timezone
            expected.update(shape=list(pixels.shape), dtype=str(pixels.dtype),
                            first_pixel_by_frame_channel=pixels[:, :, 0, 0].tolist(),
                            pixel_sum=int(pixels.sum()), tolerance=0)
            expected.setdefault("updates", []).append(dict(reason=update_reason,
                at=datetime.now(timezone.utc).isoformat()))
            from pyincucyte._atomic import write_json
            write_json(expected_path, expected)
        expected_pixels = np.broadcast_to(np.asarray(expected["first_pixel_by_frame_channel"],
                                          dtype=np.uint16)[:, :, None, None], pixels.shape)
        np.testing.assert_array_equal(pixels, expected_pixels)
        assert list(pixels.shape) == expected["shape"]
        assert str(pixels.dtype) == expected["dtype"]
        assert int(pixels.sum()) == expected["pixel_sum"]
        if show:
            client.preview(38, wells="A1", channels="phase,green").show(title="PyIncucyte — simulated device")
    return dict(verified=True, frames=2, channels=2, pixels=int(pixels.size), tolerance=0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show", action="store_true", help="Open the real preview viewer after verification")
    parser.add_argument("--update-expected", action="store_true",
                        help="Explicitly approve new expected pixels; requires --reason")
    parser.add_argument("--reason", help="Recorded reason for approving changed fixture answers")
    args = parser.parse_args()
    if args.update_expected and not (args.reason or "").strip():
        parser.error("--update-expected requires a nonempty --reason")
    if args.reason and not args.update_expected:
        parser.error("--reason is only valid with --update-expected")
    with tempfile.TemporaryDirectory(prefix="pyincucyte-demo-") as folder:
        print(json.dumps(run(Path(folder), args.show, args.reason if args.update_expected else None)))
