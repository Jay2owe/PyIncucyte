"""Public host interface for the actual vessel and well browser."""
from tkinter import ttk

from .app import App

API_VERSION = 1


def _well_name(row, column):
    row, label = int(row) + 1, ""
    while row:
        row, remainder = divmod(row - 1, 26)
        label = chr(65 + remainder) + label
    return label + str(int(column) + 1)


def selection_snapshot(app, follow=False):
    """Read the current Tk selection without exporting or including credentials."""
    ids = app._selected_vessel_ids()
    if len(ids) != 1:
        raise ValueError("Select one vessel for this workflow experiment.")
    vessel = app._vessel(ids[0])
    host = app._active_host()
    if vessel is None or not host:
        raise ValueError("Choose a connected vessel first.")
    wells = app.selected_wells.get(vessel.id)
    if wells is None:
        wells = app.scanned_wells.get(vessel.id)
    if not wells:
        raise ValueError("Wait for the well list, then select at least one well.")
    channels = app._selected_channels()
    if not channels:
        raise ValueError("Select at least one channel.")
    options = app._current_options()
    return {"connection_id": host, "experiment_id": str(vessel.id),
            "positions": sorted(_well_name(*well) for well in wells), "channels": channels,
            "start_from": options.start_from, "end_at": options.end_at,
            "follow": bool(follow)}


def create_embedded(root, on_selection, *, auto_connect=True, client=None, dark=None):
    """Keep the original browser and connection controls; the host owns collection."""
    def accept(follow=False):
        try:
            on_selection(selection_snapshot(app, follow))
        except ValueError as exc:
            app.say(str(exc), "warn")

    app = App(root, client=client, embedded=True, on_selection=accept,
              auto_connect=auto_connect, dark=dark)
    settings = ttk.Frame(app.left_column.master, padding=8)
    settings.pack(side="bottom", fill="x", before=app.left_column)
    app._build_export_form(settings, ("channels", "window"))
    app._on_window_change()
    app.download_btn.configure(text="Use in workflow", command=lambda: accept(False))
    app.sync_btn.configure(text="Follow in workflow", command=lambda: accept(True))
    for button in (app.schedule_btn, app.stop_btn, app.preview_download_btn):
        button.grid_remove()
    return app
