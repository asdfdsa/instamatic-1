from Tkinter import *
from ttk import *
from Tkinter import Label as tkLabel
from tkFont import Font, nametofont
from instamatic import version


def get_background_of_widget(widget):
    """http://code.activestate.com/recipes/580774-tkinter-link-or-hyperlink-button/"""
    try:
        # We assume first tk widget
        background = widget.cget("background")
    except:
        # Otherwise this is a ttk widget
        style = widget.cget("style")

        if style == "":
            # if there is not style configuration option, default style is the same than widget class
            style = widget.winfo_class()

        background = Style().lookup(style, 'background')
    
    return background


class Link_Button(tkLabel, object):
    """http://code.activestate.com/recipes/580774-tkinter-link-or-hyperlink-button/"""
    def __init__(self, master, text, background=None, font=None, familiy=None, size=None, underline=True, visited_fg = "#551A8B", normal_fg = "#0000EE", visited=False, action=None):
        self._visited_fg = visited_fg
        self._normal_fg = normal_fg
        
        if visited:
            fg = self._visited_fg
        else:
            fg = self._normal_fg

        if font is None:
            default_font = nametofont("TkDefaultFont")
            family = default_font.cget("family")

            if size is None:
                size = default_font.cget("size")

            font = Font(family=family, size=size, underline=underline)

        tkLabel.__init__(self, master, text=text, fg=fg, cursor="hand2", font=font)

        if background is None:
            background = get_background_of_widget(master)

        self.configure(background=background)

        self._visited = visited
        self._action = action

        self.bind("<Button-1>", self._on_click)

    @property
    def visited(self):
        return self._visited
        
    @visited.setter
    def visited(self, is_visited):
        if is_visited:
            self.configure(fg=self._visited_fg)
            self._visited = True
        else:
            self.configure(fg=self._normal_fg)
            self._visited = False

    def _on_click(self, event):
        if not self._visited:
            self.configure(fg=self._visited_fg)

        self._visited = True

        if self._action:
            self._action()


class About(LabelFrame):
    """docstring for About"""
    def __init__(self, parent):
        LabelFrame.__init__(self, parent, text="About instamatic")
        self.parent = parent

        frame = Frame(self)
        
        Label(frame, text="").grid(row=0, column=0, sticky="W")
        Label(frame, text="Author:").grid(row=1, column=0, sticky="W", padx=10)
        Label(frame, text="Stef Smeets (stef.smeets@mmk.su.se)").grid(row=1, column=1, sticky="W")
        Label(frame, text="Contributors:\n").grid(row=2, column=0, sticky="W", padx=10)
        Label(frame, text="Bin Wang (bin.wang@mmk.su.se)\n[cRED implementation]").grid(row=2, column=1, sticky="W")
        Label(frame, text="Magda Cichocka (magdalena.cichocka@mmk.su.se)\n[Testing + ideas]").grid(row=3, column=1, sticky="W")
        Label(frame, text="").grid(row=5, column=0, sticky="W")

        Label(frame, text="Source code:").grid(row=10, column=0, sticky="W", padx=10)
        link = Link_Button(frame, text="http://github.com/stefsmeets/instamatic", action=self.link_github)
        link.grid(row=10, column=1, sticky="W")
        Label(frame, text="").grid(row=12, column=0, sticky="W")

        Label(frame, text="Manual:").grid(row=20, column=0, sticky="W", padx=10)
        link = Link_Button(frame, text="http://github.com/stefsmeets/instamatic", action=self.link_github)
        link.grid(row=20, column=1, sticky="W")
        Label(frame, text="").grid(row=22, column=0, sticky="W")

        Label(frame, text="If you found this software useful, please cite:").grid(row=30, column=0, sticky="W", columnspan=2, padx=10)
        txt = Message(frame, text="Stef Smeets. (2017) Instamatic (Version {}) [Software]. Available from http://github.com/stefsmeets/instamatic".format(version.__version__), width=320, justify=LEFT)
        txt.grid(row=31, column=1, sticky="W")

        Label(frame, text="").grid(row=31, column=0, sticky="W", padx=10)

        frame.pack(side="top", fill="x")

    def link_github(self, event=None):
        import webbrowser
        webbrowser.open_new(r"http://www.github.com/stefsmeets/instamatic")

    def link_manual(self, event=None):
        import webbrowser
        webbrowser.open_new(r"http://www.github.com/stefsmeets/instamatic")


if __name__ == '__main__':
    root = Tk()
    About(root).pack(side="top", fill="both", expand=True)
    root.mainloop()
