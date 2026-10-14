"""Open the actual desktop with a simulated instrument; optionally reload on save."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def desktop(work,reload=False,check=False):
    sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
    os.environ['PYINCUCYTE_HOME']=str(work/'settings')
    from fakes import FakeDevice,patched,logged_in_store
    from pyincucyte import IncucyteClient,engine
    from pyincucyte.gui import app as app_mod
    from unittest.mock import patch
    import socket
    import requests
    import tkinter as tk
    device=FakeDevice();store=logged_in_store(work)
    with (patched(device),patch.object(app_mod,'api_post',device.api_post),
          patch.object(engine,'get_token',return_value=('test-token',3600)),
          patch.object(requests.sessions.Session,'request',side_effect=RuntimeError('Offline demo: real network requests are disabled')),
          patch.object(socket.socket,'connect',side_effect=ConnectionRefusedError('Offline demo')),
          patch.object(socket.socket,'connect_ex',return_value=1)):
        window=tk.Tk();client=IncucyteClient('10.0.0.1',store=store)
        app=app_mod.App(window,client=client,auto_connect=False);app._refresh_vessels()
        def signature():return {str(p):p.stat().st_mtime_ns for p in (ROOT/'pyincucyte').rglob('*.py')}
        original=signature();changed=[]
        def tick():
            if reload and signature()!=original:
                changed.append(True);app.on_close();return
            if check and app.vessel_tree.get_children() and not app.busy:
                app.on_close();return
            window.after(500,tick)
        window.after(500,tick);window.mainloop()
    return 75 if changed else 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reload',action='store_true');p.add_argument('--check',action='store_true')
    p.add_argument('--work',type=Path,help=argparse.SUPPRESS);a=p.parse_args()
    if a.work:raise SystemExit(desktop(a.work,a.reload,a.check))
    with tempfile.TemporaryDirectory(prefix='pyincucyte-desktop-demo-') as folder:
        command=[sys.executable,__file__,'--work',folder]
        if a.reload:command.append('--reload')
        if a.check:command.append('--check')
        while True:
            done=subprocess.run(command)
            if done.returncode!=75:raise SystemExit(done.returncode)
