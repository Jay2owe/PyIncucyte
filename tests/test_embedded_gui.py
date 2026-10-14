from types import SimpleNamespace

import pytest

from pyincucyte.gui.embedded import selection_snapshot


def app(ids=(8,), wells=None, channels=(1, 3)):
    return SimpleNamespace(_selected_vessel_ids=lambda: list(ids),
                           _vessel=lambda ident: SimpleNamespace(id=ident),
                           _active_host=lambda: "saved-device",
                           selected_wells={8: wells}, scanned_wells={8: {(0, 0), (1, 1)}},
                           _selected_channels=lambda: list(channels),
                           _current_options=lambda: SimpleNamespace(start_from="first", end_at="now"))


def test_all_selected_means_observed_wells_not_unobserved_empty_wells():
    selected = selection_snapshot(app(), True)
    assert selected == dict(connection_id="saved-device", experiment_id="8",
                            positions=["A1", "B2"], channels=[1, 3],
                            start_from="first", end_at="now", follow=True)


def test_explicit_subset_and_empty_selection_are_distinct():
    assert selection_snapshot(app(wells={(1, 1)}))["positions"] == ["B2"]
    with pytest.raises(ValueError, match="one well"):
        selection_snapshot(app(wells=set()))
    with pytest.raises(ValueError, match="one channel"):
        selection_snapshot(app(channels=()))


def test_multiple_vessels_are_not_silently_reduced_to_first():
    with pytest.raises(ValueError, match="one vessel"):
        selection_snapshot(app(ids=(8, 9)))


def test_embedded_collection_actions_only_handoff():
    from pyincucyte.gui.app import App
    calls = []
    controller = App.__new__(App)
    controller.embedded = True
    controller.watcher = None
    controller.on_selection = calls.append
    controller._download()
    controller._start_sync()
    controller._schedule_download()
    assert calls == [False, True, False]
