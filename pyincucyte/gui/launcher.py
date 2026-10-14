"""Overlap module loading with native window creation; keep every Tk call local."""
import importlib
import sys
import threading
import tkinter as tk

from . import theme


def prepare_window():
    """Return a main-thread root and the fully imported, unchanged App class."""
    theme.enable_dpi_awareness()
    name=__package__+'.app'
    module=sys.modules.get(name)
    if module is not None and hasattr(module,'App'):
        return tk.Tk(),module.App
    loaded={}
    def load():
        try:loaded['app']=importlib.import_module(name).App
        except BaseException as exc:loaded['error']=exc
    worker=threading.Thread(target=load,name='pyincucyte-desktop-import',daemon=True)
    worker.start()
    root=None
    try:
        root=tk.Tk()
        worker.join()
        if 'error' in loaded:raise loaded['error']
        return root,loaded['app']
    except BaseException:
        if root is not None:root.destroy()
        raise
    finally:
        worker.join()


def main():
    """Launch the desktop app and return its exit code."""
    root,app_class=prepare_window()
    try:app=app_class(root)
    except BaseException:
        root.destroy()
        raise
    root.protocol('WM_DELETE_WINDOW',app.on_close)
    root.mainloop()
    return 0
