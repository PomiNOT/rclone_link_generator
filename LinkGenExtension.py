from gi import require_version
require_version('Gtk', '3.0')
require_version('Nautilus', '3.0')
from gi.repository import Nautilus, GObject, Gtk, Gdk

import jwt
import time
from urllib.parse import unquote
import sys
import subprocess

SECRET = "..." #Put secret here
ENDPOINT = "..." #Put endpoint here

class LinkGenExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()

    def open_dialog(self, menu_item, file, file_name):
        if file.is_gone():
            warning("File is no longer available")
            return

        dlg = ResultDialog(file_name)
        dlg.run()
        dlg.destroy()

    def get_file_items(self, window, files):
        if len(files) != 1:
            return []

        file = files[0]
        if file.is_directory():
            return []

        fs_path = unquote(file.get_uri()[7:])
        starting_path = None
        for rclone_path in get_rclone_mounted_paths():
            if fs_path.startswith(rclone_path):
                starting_path = rclone_path
                break

        if starting_path == None:
            return []

        cloud_path = fs_path[len(starting_path) + 1:]

        item = Nautilus.MenuItem(
            name="LinkGen::generate_link",
            label="Generate Link...",
            tip=f"Generate public link for {file.get_name()}"
        )
        item.connect("activate", self.open_dialog, file, cloud_path)

        return [item]

class ResultDialog(Gtk.Dialog):
    def __init__(self, file_name):
        super().__init__(title="Generated link")

        self.set_default_size(500, 60)
        self.file_name = file_name

        self.input = Gtk.Entry()
        self.input.set_placeholder_text("Link will appear here")
        self.input.set_sensitive(False)

        copy_button = Gtk.Button.new_with_label("Copy")
        self.spin_button = Gtk.SpinButton.new_with_range(0, 86400, 1)

        btn_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 5)
        btn_box.pack_start(self.spin_button, True, True, 0)
        btn_box.pack_start(copy_button, True, True, 0)

        box = self.get_content_area()
        box.pack_start(self.input, True, True, 0)
        box.pack_start(btn_box, False, False, 5)

        copy_button.connect("clicked", self.copy)
        self.spin_button.connect("value-changed", lambda _: self.generate_link())

        self.show_all()

    def generate_link(self):
        exp_date = int(time.time()) + int(self.spin_button.get_value())
        payload = {
            "path": self.file_name,
            "exp": exp_date
        }
        token = jwt.encode(payload, SECRET, "HS256")
        link = ENDPOINT + token
        self.input.set_text(link)
        return link

    def copy(self, _):
        link = self.generate_link()

        display = Gdk.Display.get_default()
        clipboard = Gtk.Clipboard.get_default(display)
        clipboard.set_text(link, len(link))
        self.hide()


def get_rclone_mounted_paths():
    out = subprocess.check_output(["mount"]).decode(sys.stdout.encoding)
    rclone_filter = filter(lambda line: "fuse.rclone" in line, out.splitlines())
    mount_paths = [line.split()[2] for line in rclone_filter]
    return mount_paths

def warning(message):
    dlg = Gtk.MessageDialog(
        None,
        Gtk.DialogFlags.MODAL,
        Gtk.MessageType.INFO,
        Gtk.ButtonsType.OK,
        message
    )

    dlg.run()
    dlg.destroy()
