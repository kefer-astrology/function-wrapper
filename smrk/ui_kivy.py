from context import Actual, combine_date_time, now
from current import Observation, Almanac
from display import figure_3d
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.app import MDApp
from kivy.lang import Builder
from settings import change_language

class MyApp(MDApp):
    def prepare_content(self, date: str="", place: str=""):
        # 1 - initial setting
        self.date = Actual()
        self.location = Actual(t="place")
        #self.name = ""
    
    def draw_content(self, name="Johny"):
        self.name = name
        look = Observation(  # Prague hardcode for now
                lat=50.08804,  # first_event_place.value.latitude,
                lon=14.42076,  # first_event_place.value.longitude,
                )
        planets = look.where_is(self.date, of="altaz")
        return figure_3d(planets)

    def build(self):
        return Builder.load_file("ui_kivy.kv")

    def show_message(self, message):
        dialog = MDDialog(
            title=message,
            size_hint=(0.7, 1),
            buttons=[MDRaisedButton(text="Close", on_release=self.close_dialog)],
        )
        dialog.open()

    def close_dialog(self, *args):
        self.root_window.children[0].dismiss()

if __name__ == '__main__':
    lang = change_language(default="cz")
    MyApp().run()
