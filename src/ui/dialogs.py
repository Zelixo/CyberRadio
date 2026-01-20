from gi.repository import Gtk, Adw

class AddStationDialog(Adw.Window):
    def __init__(self, parent_window, on_save_callback):
        super().__init__(modal=True, transient_for=parent_window)
        self.set_title("Add Custom Station")
        self.set_default_size(400, 300)
        self.on_save = on_save_callback

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(30)
        box.set_margin_bottom(30)
        box.set_margin_start(30)
        box.set_margin_end(30)
        self.set_content(box)

        label = Gtk.Label(label="Enter Station Details")
        label.add_css_class("title-1")
        box.append(label)

        self.name_entry = Adw.EntryRow(title="Station Name")
        self.url_entry = Adw.EntryRow(title="Stream URL")

        group = Adw.PreferencesGroup()
        group.add(self.name_entry)
        group.add(self.url_entry)
        box.append(group)

        btns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btns_box.set_halign(Gtk.Align.CENTER)
        box.append(btns_box)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda x: self.close())
        btns_box.append(cancel_btn)

        save_btn = Gtk.Button(label="Add Station")
        save_btn.add_css_class("suggested-action")
        save_btn.add_css_class("pill")
        save_btn.connect("clicked", self.on_save_clicked)
        btns_box.append(save_btn)

    def on_save_clicked(self, btn):
        name = self.name_entry.get_text()
        url = self.url_entry.get_text()
        if name and url:
            station_data = {
                "name": name,
                "url_resolved": url,
                "countrycode": "Custom",
                "url": url,
                "favicon": None
            }
            self.on_save(station_data)
            self.close()
