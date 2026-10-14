"""Native window ownership and failure cleanup for concurrent module loading."""
import sys
import threading
from types import SimpleNamespace
import pytest
from pyincucyte.gui import launcher


class Root:
    def __init__(self):self.destroyed=False
    def destroy(self):self.destroyed=True


def setup_cold(monkeypatch):
    monkeypatch.delitem(sys.modules,launcher.__package__+'.app',raising=False)
    monkeypatch.setattr(launcher.theme,'enable_dpi_awareness',lambda:None)


def test_import_overlaps_window_creation_and_leaves_tk_on_caller(monkeypatch):
    setup_cold(monkeypatch)
    started=threading.Event();created=threading.Event();owners={};root=Root()
    app_class=type('App',(),{})
    def load(name):
        owners['import']=threading.get_ident();started.set()
        assert created.wait(5),'Tk construction must overlap module loading'
        return SimpleNamespace(App=app_class)
    def make_root():
        owners['tk']=threading.get_ident()
        assert started.wait(5)
        created.set();return root
    monkeypatch.setattr(launcher.importlib,'import_module',load)
    monkeypatch.setattr(launcher.tk,'Tk',make_root)
    assert launcher.prepare_window()==(root,app_class)
    assert owners['tk']==threading.get_ident()!=owners['import']


def test_warm_import_uses_actual_class_without_an_extra_worker(monkeypatch):
    app_class=type('App',(),{});root=Root()
    monkeypatch.setitem(sys.modules,launcher.__package__+'.app',SimpleNamespace(App=app_class))
    monkeypatch.setattr(launcher.theme,'enable_dpi_awareness',lambda:None)
    monkeypatch.setattr(launcher.tk,'Tk',lambda:root)
    def unexpected(*args,**kwargs):raise AssertionError('Warm launch needs no import worker')
    monkeypatch.setattr(launcher.threading,'Thread',unexpected)
    assert launcher.prepare_window()==(root,app_class)


def test_import_failure_destroys_created_root_and_preserves_error(monkeypatch):
    setup_cold(monkeypatch);root=Root()
    monkeypatch.setattr(launcher.tk,'Tk',lambda:root)
    def fail(name):raise ImportError('missing image dependency')
    monkeypatch.setattr(launcher.importlib,'import_module',fail)
    with pytest.raises(ImportError,match='missing image dependency'):launcher.prepare_window()
    assert root.destroyed


def test_window_failure_joins_import_worker(monkeypatch):
    setup_cold(monkeypatch);loaded=threading.Event()
    def load(name):loaded.set();return SimpleNamespace(App=object)
    def fail():raise RuntimeError('no display')
    monkeypatch.setattr(launcher.importlib,'import_module',load)
    monkeypatch.setattr(launcher.tk,'Tk',fail)
    with pytest.raises(RuntimeError,match='no display'):launcher.prepare_window()
    assert loaded.is_set()


def test_application_construction_failure_releases_window(monkeypatch):
    root=Root()
    def fail(*args,**kwargs):raise ValueError('invalid saved state')
    monkeypatch.setattr(launcher,'prepare_window',lambda:(root,fail))
    with pytest.raises(ValueError,match='invalid saved state'):launcher.main()
    assert root.destroyed
