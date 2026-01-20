import os
import shutil
from gi.repository import Gtk, Adw, Gio, GObject

class AddStationDialog(Adw.Window):
    def __init__(self, parent_window, on_save_callback, station_data=None):
        super().__init__(modal=True, transient_for=parent_window)
        self.set_title("Edit Station" if station_data else "Add Custom Station")
        self.set_default_size(400, 350)
        self.on_save = on_save_callback
        self.edit_data = station_data

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
        
        if station_data:
            self.name_entry.set_text(station_data.get('name', ''))
            self.url_entry.set_text(station_data.get('url_resolved', '') or station_data.get('url', ''))

        # Icon Row with Browse Button
        self.icon_entry = Adw.EntryRow(title="Icon URL or Local Path")
        if station_data:
            self.icon_entry.set_text(station_data.get('favicon', '') or '')

        browse_btn = Gtk.Button(icon_name="folder-open-symbolic")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.set_margin_end(10)
        browse_btn.add_css_class("flat")
        browse_btn.connect("clicked", self.on_browse_clicked)

        group = Adw.PreferencesGroup()
        group.add(self.name_entry)
        group.add(self.url_entry)
        box.append(group)
        
        icon_group = Adw.PreferencesGroup(title="Station Icon")
        icon_row = Adw.ActionRow(title="Select Icon")
        icon_row.add_suffix(browse_btn)
        icon_group.add(icon_row)
        icon_group.add(self.icon_entry)
        box.append(icon_group)

        btns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btns_box.set_halign(Gtk.Align.CENTER)
        box.append(btns_box)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda x: self.close())
        btns_box.append(cancel_btn)

        save_btn = Gtk.Button(label="Save Changes" if station_data else "Add Station")
        save_btn.add_css_class("suggested-action")
        save_btn.add_css_class("pill")
        save_btn.connect("clicked", self.on_save_clicked)
        btns_box.append(save_btn)

    def on_browse_clicked(self, btn):
        dialog = Gtk.FileChooserNative(
            title="Select Station Icon",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Images")
        filter_img.add_mime_type("image/png")
        filter_img.add_mime_type("image/jpeg")
        filter_img.add_mime_type("image/svg+xml")
        dialog.add_filter(filter_img)

        dialog.connect("response", self.on_file_response)
        dialog.show()

    def on_file_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            file_path = dialog.get_file().get_path()
            self.icon_entry.set_text(file_path)
        dialog.destroy()

    def on_save_clicked(self, btn):
        name = self.name_entry.get_text()
        url = self.url_entry.get_text()
        icon = self.icon_entry.get_text()
        
        if name and url:
            final_icon = icon
            
            # If it's a local file, copy it to the config dir for persistence
            if icon and os.path.exists(icon):
                try:
                    config_icon_dir = os.path.expanduser("~/.config/CyberRadio/icons")
                    os.makedirs(config_icon_dir, exist_ok=True)
                    
                    filename = os.path.basename(icon)
                    dest_path = os.path.join(config_icon_dir, filename)
                    
                    if icon != dest_path:
                        shutil.copy2(icon, dest_path)
                    
                    final_icon = dest_path
                except Exception as e:
                    print(f"Failed to copy icon: {e}")

            station_data = {
                "name": name,
                "url_resolved": url,
                "countrycode": "Custom",
                "url": url,
                "favicon": final_icon if final_icon else None
            }
            
            # If we were editing, we might want to preserve some IDs or just pass the whole thing
            if self.edit_data:
                # Merge or replace. Since the favorites list works by URL, we'll handle the logic in main_window
                pass
                
            self.on_save(station_data, self.edit_data)
            self.close()