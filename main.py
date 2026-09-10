from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class BalochFXApp(App):
    def build(self):
        layout = BoxLayout(orientation="vertical", padding=30, spacing=20)

        title = Label(text="BALOCHFX", font_size=32)
        price = Label(text="BTC/USD\nPrice: --", font_size=24)
        signal = Label(text="SIGNAL: WAIT", font_size=26)

        button = Button(text="GET SIGNAL", font_size=22)

        layout.add_widget(title)
        layout.add_widget(price)
        layout.add_widget(signal)
        layout.add_widget(button)

        return layout

BalochFXApp().run()
