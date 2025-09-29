from kivy.animation import Animation
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, NumericProperty

from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText  # v2 API
from kivymd.uix.dialog import MDDialog

from utils import Actual, combine_date_time, now_utc
from workspace import change_language

class MyApp(MDApp):
    # top-level view: "aspects", "transits", "progressions", "synastry"
    current_view = StringProperty("aspects")
    current_view_title = StringProperty("Aspects")
    # people
    people = ListProperty(["Johny", "Bob", "Carol", "Dave"])
    current_person_index = NumericProperty(0)
    current_person_name = StringProperty("Johny")

    def build(self):
        self.title = "Kefer Astrology"
        # KivyMD v2 theming examples (optional)
        self.theme_cls.primary_palette = "Blue"
        # self.theme_cls.theme_style = "Light"
        return Builder.load_file("ui_kivy.kv")

    def on_start(self):
        # move initialization here so UI is ready
        self.prepare_content()
        # ensure UI reflects defaults
        self._update_person_buttons()
        self._update_view_title()

    # ---------- domain init ----------
    def prepare_content(self, date: str="", place: str=""):
        # 1 - initial setting
        # Initialize your domain objects here (avoid touching widgets until on_start)
        self.location = Actual(t="place")
        #self.name = ""
    
    # ---------- toolbar actions (non-top-level ones) ----------
    def on_toolbar(self, action: str):
        self.show_message(f"{action.replace('_', ' ').title()} clicked")

    # ---------- top-level view switching ----------
    def set_view(self, name: str):
        name = (name or "").lower()
        titles = {
            "aspects": "Aspects",
            "transits": "Transits",
            "progressions": "Progressions",
            "synastry": "Synastry",
        }
        if name not in titles:
            return
        self.current_view = name
        self.current_view_title = titles[name]
        # update central header label (bound via app.current_view_title in KV)
        # if you later add per-view widgets, do that here

    def _update_view_title(self):
        titles = {
            "aspects": "Aspects",
            "transits": "Transits",
            "progressions": "Progressions",
            "synastry": "Synastry",
        }
        self.current_view_title = titles.get(self.current_view, "Aspects")

    # ---------- person switching ----------
    def set_person(self, index: int):
        if not (0 <= index < len(self.people)):
            return
        self.current_person_index = index
        self.current_person_name = self.people[index]
        # reflect in inputs
        ids = self.root.ids
        if "subject_name" in ids:
            ids["subject_name"].text = self.current_person_name
        # update chip-like buttons
        self._update_person_buttons()

    def _update_person_buttons(self):
        ids = self.root.ids
        # styles: filled for selected, text for others
        btn_ids = ["person_btn_0", "person_btn_1", "person_btn_2", "person_btn_3"]
        for i, bid in enumerate(btn_ids):
            btn = ids.get(bid)
            if not btn:
                continue
            btn.style = "filled" if i == self.current_person_index else "text"

    # ---------- expand/collapse sections ----------
    def toggle_section(self, which: str):
        ids = self.root.ids
        mapping = {
            "subject": ids.get("subject_content"),
            "time": ids.get("time_content"),
            "transits": ids.get("transits_content"),
            "objects": ids.get("objects_content"),
        }
        content = mapping.get(which)
        if not content:
            return

        is_collapsed = content.height <= 1
        if is_collapsed:
            target = 200
            Animation.stop_all(content)
            Animation(height=target, opacity=1, d=0.18, t="out_quad").start(content)
        else:
            Animation.stop_all(content)
            Animation(height=0, opacity=0, d=0.18, t="out_quad").start(content)

    # ---------- Bottom pseudo-tabs ----------
    def set_tab(self, name: str):
        self.root.ids.tabs_manager.current = name

    def draw_content(self, name="Johny"):
        self.name = name
        # return figure_3d()

    # ---------- dialogs ----------
    def show_message(self, message: str):
        close_btn = MDButton(MDButtonText(text="Close"), style="filled")
        close_btn.bind(on_release=self.close_dialog)
        self.dialog = MDDialog(title="Info", text=message, buttons=[close_btn])
        self.dialog.open()

    def close_dialog(self, *_):
        dlg = getattr(self, "dialog", None)
        if dlg:
            dlg.dismiss()
            self.dialog = None

if __name__ == '__main__':
    # if you pass CLI args to your script, this avoids Kivy consuming them
    # import os
    # os.environ.setdefault("KIVY_NO_ARGS", "1")
    # in case custom translation needed
    # from workspace import change_language
    lang = change_language(default="cz")
    MyApp().run()
