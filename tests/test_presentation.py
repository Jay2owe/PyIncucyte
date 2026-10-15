"""Exercise native controls introduced by the accepted interface redesign."""
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk
import pytest
from pyincucyte.gui.theme import Theme
from pyincucyte.gui.presentation import ChannelButtons, FrameSlider, section_form

@pytest.fixture(scope="module")
def desktop():
    root=tk.Tk();root.geometry("1000x700")
    yield root
    root.destroy()


def test_channel_buttons_emit_one_selection_and_rebuild_for_another_field(desktop):
    selected=tk.StringVar(value="Phase");events=[]
    channels=ChannelButtons(desktop,textvariable=selected,values=["Phase","Green"])
    channels.pack();channels.bind("<<ComboboxSelected>>",lambda e:events.append(selected.get()))
    desktop.update();channels.winfo_children()[1].invoke();desktop.update()
    assert selected.get()=="Green" and events==["Green"]
    channels.configure(values=["Phase","Red"])
    channels.winfo_children()[1].invoke();desktop.update()
    assert selected.get()=="Red" and events==["Green","Red"]


def test_frame_slider_clamps_clicks_and_programmatic_values_do_not_start_requests(desktop):
    theme=Theme(desktop);value=tk.IntVar(value=0);requests=[]
    slider=FrameSlider(desktop,theme=theme,variable=value,command=requests.append,to=7)
    slider.pack(fill="x");desktop.update()
    slider._choose(SimpleNamespace(x=5000))
    assert value.get()==7 and requests==["7.0"]
    value.set(3);desktop.update()
    assert requests==["7.0"]
    slider._move(-1)
    assert value.get()==2 and len(requests)==2
    slider.configure(to=1);slider._move(10)
    assert value.get()==1
    slider.destroy();value.set(0);desktop.update()


def test_settings_tabs_and_narrow_reflow_preserve_live_values_and_controls(desktop):
    form=ttk.Frame(desktop);form.pack(fill="both",expand=True)
    entries=[]
    for row,name in enumerate(["Output","Channels","From","To","Layout","Calibration","Options"]):
        ttk.Label(form,text=name).grid(row=row,column=0)
        entry=ttk.Entry(form);entry.insert(0,name+" draft");entry.grid(row=row,column=1)
        entries.append(entry)
    section_form(form,Theme(desktop));desktop.update()
    for size in ["1000x700","800x600","1200x800"]:
        desktop.geometry(size);desktop.update()
        for tab in form._sections.tabs():
            form._sections.select(tab);desktop.update()
        assert [e.get() for e in entries]==[n+" draft" for n in ["Output","Channels","From","To","Layout","Calibration","Options"]]
    form._sections.select(0);desktop.update()
    assert entries[0].winfo_ismapped()


def test_closed_modal_releases_its_own_tcl_variables_on_the_ui_thread(desktop):
    import weakref
    from pyincucyte.gui.dialogs import ModalDialog
    dialog=ModalDialog(desktop,Theme(desktop),"Verification")
    dialog.status_var=tk.StringVar(master=dialog,value="Draft")
    reference=weakref.ref(dialog.status_var)
    dialog.destroy()
    assert reference() is None


def test_resize_reuses_plate_items_and_preserves_hit_targets(desktop):
    from pyincucyte.gui.widgets import WellPlate
    window=tk.Toplevel(desktop);window.geometry("800x400")
    plate=WellPlate(window,Theme(desktop),rows=4,cols=6,max_cell=30)
    plate.pack(fill="both",expand=True);plate.select_all();window.update()
    original=plate.canvas.find_all();selection=plate.selection
    window.geometry("840x420");window.update()
    assert plate.canvas.find_all()==original
    cell,gap,left,top=plate._geometry
    assert plate._cell_at(left+cell/2,top+cell/2)==(0,0)
    window.geometry("160x150");window.update()
    assert plate.canvas.find_all()!=original
    assert plate.selection==selection
    cell,gap,left,top=plate._geometry
    assert plate._cell_at(left+cell/2,top+cell/2)==(0,0)
    window.destroy()



def test_fixed_workspace_keeps_layout_and_draft_when_window_resizes(desktop):
    from pyincucyte.gui.presentation import arrange_workspace
    from pyincucyte.gui.widgets import Card
    from pyincucyte.gui.app import App
    window=tk.Toplevel(desktop);window.geometry("1200x800")
    workspace=ttk.Frame(window);workspace.pack(fill="both",expand=True)
    cards=[Card(workspace,title=name,theme=Theme(desktop)) for name in ("Experiments","Images","Summary")]
    for card,cell in zip(cards,[(0,0),(1,0),(1,1)]):card.grid(row=cell[0],column=cell[1])
    tree=ttk.Treeview(cards[0].body,columns="name last channels plate id owner".split(),show="headings")
    tree.pack(fill="both",expand=True);tree.insert("", "end",iid="example",values=["Example"]);tree.selection_set("example")
    draft=ttk.Entry(cards[2].body);draft.insert(0,"Keep this draft");draft.pack()
    arrange_workspace(workspace,tree)
    app=App.__new__(App);app.left_column=workspace
    app.wells_card=cards[1];app.well_count_var=tk.StringVar(master=window)
    fold=app._set_wells_expanded
    for geometry in ("1200x800","800x650","1400x900"):
        window.geometry(geometry)
        for expanded in (False,True):
            fold(expanded);window.update()
            assert all(card.winfo_manager()=="grid" and card.winfo_ismapped() for card in cards)
            assert not any(isinstance(w,tk.PanedWindow) for w in workspace.winfo_children())
            assert cards[0].winfo_x()==cards[2].winfo_x()<cards[1].winfo_x()
            assert cards[0].winfo_y()<cards[2].winfo_y()
            assert int(cards[1].grid_info()["rowspan"])==2
            assert draft.get()=="Keep this draft" and tree.selection()==("example",)
    window.destroy()


@pytest.mark.parametrize("rows,cols",[(2,3),(3,4),(4,6),(6,8),(8,12),(16,24)])
def test_plate_scales_to_available_space_with_working_headers(desktop, rows, cols):
    from pyincucyte.gui.widgets import WellPlate
    window=tk.Toplevel(desktop);window.geometry("820x620")
    plate=WellPlate(window,Theme(desktop),rows=rows,cols=cols)
    plate.pack(fill="both",expand=True);plate.select_all();window.update()
    for geometry in ("820x620","420x310"):
        window.geometry(geometry);window.update()
        cell,gap,left,top=plate._geometry
        assert left+cols*(cell+gap)<=plate.canvas.winfo_width()
        assert top+rows*(cell+gap)<=plate.canvas.winfo_height()
        if rows<=4:assert cell>30
        assert plate._cell_at(left+(cols-1)*(cell+gap)+cell/2,top+(rows-1)*(cell+gap)+cell/2)==(rows-1,cols-1)
        assert plate._header_at(left+cell/2,top-gap-plate._label_margin()/2)==("col",0)
        assert plate._header_at(left-gap-plate._label_margin()/2,top+cell/2)==("row",0)
        assert plate.count==rows*cols
    # A real cell click still toggles the intended well after resizing.
    plate.canvas.event_generate("<Button-1>",x=int(left+cell/2),y=int(top+cell/2))
    plate.canvas.event_generate("<ButtonRelease-1>",x=int(left+cell/2),y=int(top+cell/2));window.update()
    assert (0,0) not in plate.selection and plate.count==rows*cols-1
    window.destroy()
