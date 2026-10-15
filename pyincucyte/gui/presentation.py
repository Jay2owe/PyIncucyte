"""Native presentation controls. Instrument pixels and export values stay untouched."""
import tkinter as tk
from tkinter import ttk, font as tkfont
from . import theme as theme_mod
from .widgets import tip


class ChannelButtons(ttk.Frame):
    """A channel selector retaining the combobox event/value contract."""
    def __init__(self, parent, *, textvariable, values=(), **kwargs):
        kwargs.pop("state", None)
        kwargs.pop("width", None)
        super().__init__(parent, style="Toolbar.TFrame", **kwargs)
        self.variable = textvariable
        self.configure(values=values)

    def configure(self, cnf=None, **kwargs):
        if "values" in kwargs:
            values = list(kwargs.pop("values"))
            for child in self.winfo_children():
                child.destroy()
            for index, label in enumerate(values):
                ttk.Radiobutton(self, text=label, value=label,
                    variable=self.variable, style="Channel.Toolbutton",
                    command=lambda: self.event_generate("<<ComboboxSelected>>")
                    ).grid(row=index // 4, column=index % 4, sticky="ew", padx=2, pady=2)
        return super().configure(cnf, **kwargs)


class FrameSlider(tk.Canvas):
    """A thin time track with frame snapping, mouse and keyboard control."""
    def __init__(self, parent, *, theme, variable, command, from_=0, to=0, **kwargs):
        kwargs.pop("orient", None)
        super().__init__(parent, height=26, highlightthickness=0, bd=0,
                         background=theme["surface"], takefocus=True, **kwargs)
        self.theme, self.variable, self.command = theme, variable, command
        self.minimum, self.maximum = float(from_), float(to)
        self._trace = variable.trace_add("write", self._redraw)
        self.bind("<Configure>", self._redraw)
        self.bind("<Button-1>", self._choose)
        self.bind("<B1-Motion>", self._choose)
        self.bind("<Left>", lambda e: self._move(-1))
        self.bind("<Right>", lambda e: self._move(1))
        self.bind("<Home>", lambda e: self._set(self.minimum))
        self.bind("<End>", lambda e: self._set(self.maximum))
        self.bind("<FocusIn>", self._redraw)
        self.bind("<FocusOut>", self._redraw)
        self.bind("<Destroy>", self._cleanup, add="+")

    def _cleanup(self, event):
        if event.widget is self:
            self.variable.trace_remove("write", self._trace)

    def configure(self, cnf=None, **kwargs):
        if "to" in kwargs:
            self.maximum = float(kwargs.pop("to"))
        if "from_" in kwargs:
            self.minimum = float(kwargs.pop("from_"))
        result = super().configure(cnf, **kwargs)
        if hasattr(self, "variable"):
            self._redraw()
        return result

    def _set(self, value):
        value = max(self.minimum, min(self.maximum, round(value)))
        self.variable.set(value)
        self.command(str(value))
        return "break"

    def _move(self, delta):
        return self._set(float(self.variable.get()) + delta)

    def _choose(self, event):
        self.focus_set()
        fraction = max(0, min(1, (event.x - 10) / max(1, self.winfo_width() - 20)))
        return self._set(self.minimum + fraction * (self.maximum - self.minimum))

    def _redraw(self, *_):
        if not self.winfo_exists():
            return
        self.delete("all")
        w, y = max(21, self.winfo_width()), 13
        fraction = (float(self.variable.get()) - self.minimum) / max(1, self.maximum - self.minimum)
        x = 10 + max(0, min(1, fraction)) * (w - 20)
        self.create_line(10, y, w-10, y, fill=self.theme["border"], width=4, capstyle="round")
        self.create_line(10, y, x, y, fill=self.theme["accent"], width=4, capstyle="round")
        self.create_oval(x-6, y-6, x+6, y+6, fill=self.theme["accent"], outline=self.theme["surface"], width=2)
        if self.focus_get() is self:
            self.create_rectangle(1, 1, w-2, 25, outline=self.theme["accent"], dash=(2, 2))


def arrange_workspace(workspace, tree):
    """Experiments above actions on the left; the image area owns the right."""
    panels = sorted(workspace.grid_slaves(), key=lambda w:(int(w.grid_info()["row"]), int(w.grid_info()["column"])))
    experiments, images, summary = panels
    workspace._fixed_workspace = True
    workspace.columnconfigure(0, weight=2, minsize=280, uniform="workspace")
    workspace.columnconfigure(1, weight=3, minsize=400, uniform="workspace")
    workspace.rowconfigure(0, weight=1, minsize=180)
    workspace.rowconfigure(1, weight=0)
    experiments.grid(row=0, column=0, columnspan=1, rowspan=1,
                     sticky="nsew", padx=(0, 8), pady=(0, 8))
    summary.grid(row=1, column=0, columnspan=1, rowspan=1,
                 sticky="nsew", padx=(0, 8), pady=(0, 8))
    images.grid(row=0, column=1, columnspan=1, rowspan=2,
                sticky="nsew", padx=0, pady=(0, 8))
    # A short list remains readable; all metadata is available horizontally.
    tree.configure(height=7)
    for widget in experiments.actions.winfo_children():
        if hasattr(widget,"entry"):
            widget.entry.configure(width=12)
    # Reorder the display only: stored row values and sorting keep their keys.
    tree.configure(displaycolumns=("name", "last", "channels", "plate", "id", "owner"))
    widths = {"name": 180, "last": 124, "channels": 110, "plate": 60, "id": 42, "owner": 80}
    for column, width in widths.items():
        tree.column(column, width=width, minwidth=140 if column == "name" else width,
                    stretch=column == "name", anchor="e" if column == "id" else "w")
    horizontal = ttk.Scrollbar(tree.master, orient="horizontal", command=tree.xview)
    horizontal.pack(side="bottom", fill="x", before=tree)
    tree.configure(xscrollcommand=horizontal.set)


def section_form(form, theme):
    """Group an existing form without recreating controls or their callbacks."""
    rows = {}
    for child in form.winfo_children():
        if child.winfo_manager()=="grid":
            info=child.grid_info()
            rows.setdefault(int(info["row"]), []).append((int(info["column"]),child))
    groups=[]
    for row, items in sorted(rows.items()):
        items.sort(key=lambda pair:pair[0])
        if len(items)==2 and isinstance(items[0][1],ttk.Label):
            groups.append((items[0][1],items[1][1]))
    if not groups:
        return
    for label, value in groups:
        label.grid_forget();value.grid_forget()
    for column in range(4):
        form.columnconfigure(column,weight=0)
    form.columnconfigure(0,weight=1)
    form.rowconfigure(0,weight=1)
    book=ttk.Notebook(form,style="Settings.TNotebook")
    book.grid(row=0,column=0,sticky="nsew")
    pages={}
    order=("Download", "Image processing", "Automation", "Advanced")
    sections={name:[] for name in order}
    for label,value in groups:
        text=str(label.cget("text"))
        group=("Download" if text in ("Output","Channels","From","To","Layout") else
               "Image processing" if text in ("Calibration","Image processing") else
               "Automation" if text in ("Sync","Check for scans","Batch new frames") else "Advanced")
        sections[group].append((label,value))
    for name in order:
        if not sections[name]:continue
        page=ttk.Frame(book,style="Surface.TFrame",padding=12)
        book.add(page,text=name)
        page.columnconfigure(0,weight=1)
        for index,(label,value) in enumerate(sections[name]):
            label.grid(in_=page,row=index*2,column=0,sticky="w",pady=(10 if index else 0,4))
            value.grid(in_=page,row=index*2+1,column=0,sticky="ew",pady=(0,8))
            label.lift();value.lift()
            if isinstance(value,(ttk.Entry,ttk.Combobox)):
                value.configure(width=24)
            # Replace wide checkbox/radio runs with vertically readable choices.
            controls=value.winfo_children()
            if controls and all(isinstance(w,(ttk.Radiobutton,ttk.Checkbutton)) for w in controls):
                for w in controls:
                    if w.winfo_manager()=="pack":w.pack_forget()
                    else:w.grid_forget()
                for i,w in enumerate(controls):
                    w.grid(row=i,column=0,sticky="w",pady=3)
                    if isinstance(w,ttk.Radiobutton):w.configure(style="Choice.TRadiobutton")
        pages[name]=page
    def reflow(event=None):
        columns=2 if form.winfo_width()>950 else 1
        if getattr(form,"_form_columns",None)==columns:return
        form._form_columns=columns
        for name,page in pages.items():
            for col in range(2):page.columnconfigure(col,weight=1 if col<columns else 0,uniform="fields")
            index=0
            for label,value in sections[name]:
                wide=str(label.cget("text"))=="Output"
                if wide:
                    row,col,span=0,0,columns
                else:
                    row,col,span=(index//columns+1)*2,index%columns,1
                    index+=1
                label.grid_configure(row=row,column=col,columnspan=span,padx=(0,16),pady=(12,4))
                value.grid_configure(row=row+1,column=col,columnspan=span,padx=(0,16),pady=(0,10))
    form.bind("<Configure>",reflow,add="+")
    form.after_idle(reflow)
    form._sections=book


def instrument_panel(body, theme, name, *, plate=False):
    """Original instrument illustration beside existing connection controls."""
    # Reserve a separate column; form widgets keep their original parents.
    body.columnconfigure(0,weight=0)
    body.columnconfigure(1,weight=1)
    art=tk.Canvas(body,width=220,height=340,highlightthickness=0,background=theme["accent_soft"])
    art.grid(row=0,column=2,rowspan=20,sticky="ns",padx=(24,0))
    c=theme
    art.create_text(24,34,text=name,anchor="w",font=theme.font_title,fill=c["accent"])
    if plate:
        art.create_rectangle(35,100,185,250,fill=c["surface"],outline=c["border_strong"],width=2)
        art.create_rectangle(49,117,171,185,fill=c["surface_alt"],outline=c["border"])
        for r in range(3):
            for col in range(5):
                x,y=61+col*24,130+r*20
                art.create_oval(x-5,y-5,x+5,y+5,fill=c["accent_soft"],outline=c["accent"])
        art.create_rectangle(53,211,166,219,fill=c["accent"],outline="")
    else:
        art.create_rectangle(36,117,183,265,fill=c["surface"],outline=c["border_strong"],width=2)
        art.create_rectangle(48,133,171,217,fill=c["surface_alt"],outline=c["border"])
        art.create_rectangle(99,143,120,171,fill=c["accent"],outline="")
        art.create_oval(92,176,128,188,fill=c["accent_soft"],outline=c["accent"])
        art.create_rectangle(63,197,158,202,fill=c["text_muted"],outline="")
        art.create_oval(143,235,156,248,fill=c["accent"],outline="")
    art.create_text(24,304,text="INSTRUMENT CONNECTION",anchor="w",font=theme.font_small,fill=c["text_muted"])
    # Supplementary explanation stays available as help, not a wall of text.
    for child in body.winfo_children():
        if isinstance(child,ttk.Label) and child.winfo_manager()=="grid" and int(child.grid_info()["row"])==1:
            tip(art,str(child.cget("text")),theme);child.grid_remove()
    body.winfo_toplevel().minsize(740,440)


def settings_help(body, theme):
    """Move secondary modal explanations behind a labelled disclosure."""
    for child in list(body.winfo_children()):
        if isinstance(child,ttk.Label) and child.winfo_manager()=="grid" and int(child.grid_info()["row"])==1:
            text=str(child.cget("text"));child.grid_remove()
            help_button=ttk.Button(body,text="How scheduling works",style="Ghost.TButton",
                command=lambda w=child:w.grid() if not w.winfo_ismapped() else w.grid_remove())
            help_button.grid(row=0,column=1,sticky="e")
            tip(help_button,text,theme)


def draw_protocol(canvas, record, theme, layout, zoom=1.0, on_detail=None):
    """Render the package's authoritative vector shapes, with readable fit."""
    width,height,shapes=layout(record,theme="dark" if theme.dark else "light")
    scale=max(.65,min(1.5,(max(640,canvas.winfo_width())-32)/width))*zoom
    canvas.delete("all");canvas.configure(background=theme["bg"])
    fonts=[]
    for s in shapes:
        kind=s["kind"];item=None
        if kind=="rect":
            x,y,w,h=[s[k]*scale for k in ("x","y","w","h")]
            item=canvas.create_rectangle(x,y,x+w,y+h,fill=s["fill"],outline=s.get("stroke") or "",width=max(1,(s.get("width") or 1)*scale))
        elif kind=="circle":
            x,y,r=[s[k]*scale for k in ("cx","cy","r")]
            item=canvas.create_oval(x-r,y-r,x+r,y+r,fill=s["fill"],outline="")
        elif kind=="text":
            f=tkfont.Font(family=theme.family,size=-max(9,round(s["size"]*scale)),weight=s["weight"])
            fonts.append(f)
            item=canvas.create_text(s["x"]*scale,s["y"]*scale+f.metrics("descent"),text=s["text"],fill=s["fill"],font=f,anchor={"start":"sw","middle":"s","end":"se"}[s["anchor"]])
        elif kind=="line":
            item=canvas.create_line(*[s[k]*scale for k in ("x1","y1","x2","y2")],fill=s["stroke"],width=max(1,s["width"]*scale))
        elif kind in ("polyline","poly"):
            pts=[v*scale for point in s["points"] for v in point]
            item=(canvas.create_line(*pts,fill=s["stroke"],width=max(1,s["width"]*scale)) if kind=="polyline" else canvas.create_polygon(*pts,fill=s["fill"],outline=""))

        if item and s.get("title") and on_detail:
            canvas.tag_bind(item,"<Enter>",lambda e,text=s["title"]:on_detail(text))
    canvas._protocol_fonts=fonts
    canvas.configure(scrollregion=(0,0,width*scale,height*scale))


def scroll_settings(parent, theme):
    viewport=ttk.Frame(parent,style="Surface.TFrame")
    canvas=tk.Canvas(viewport,background=theme["surface"],highlightthickness=0,bd=0)
    bar=ttk.Scrollbar(viewport,orient="vertical",command=canvas.yview)
    bar.pack(side="right",fill="y");canvas.pack(side="left",fill="both",expand=True)
    canvas.configure(yscrollcommand=bar.set)
    form=ttk.Frame(canvas,style="Surface.TFrame")
    item=canvas.create_window((0,0),window=form,anchor="nw")
    form.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",lambda e:canvas.itemconfigure(item,width=e.width))
    def wheel(e):
        if canvas.yview()!=(0.0,1.0):canvas.yview_scroll(int(-e.delta/120),"units")
    # Bind this owned window only, so scrolling never affects another app.
    parent.winfo_toplevel().bind("<MouseWheel>",wheel,add="+")
    return viewport,form
