"""Tkinter desktop front end for PyIncucyte."""

from .launcher import main


def __getattr__(name):
    if name!='App':raise AttributeError(name)
    from .app import App
    globals()['App']=App
    return App


def __dir__():
    return sorted(set(globals())|{'App'})

__all__ = ["App", "main"]
