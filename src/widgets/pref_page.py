# pref_page.py
#
# Copyright 2026 Nathan Perlman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import gi, os, shutil
from gi.repository import Gtk, Adw, GLib, Xdp
from .extra_options_box import OptionsBox
from .accent_box import AccentBox
from .utils import change_autostart, open_toast


class PrefPage(Gtk.Box):
    def __init__(self, win):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            valign=Gtk.Align.CENTER,
            spacing=32,
            margin_start=12,
            margin_end=12,
        )

        if(not "GNOME" in GLib.getenv("XDG_CURRENT_DESKTOP") or ""):
            self.append(Adw.Clamp(maximum_size=800, child=AccentBox(win)))
        self.append(OptionsBox(win))
        prefs_page = Adw.PreferencesGroup()
        prefs_page.set_title(_("Preferences"))

        toggle_group = Adw.PreferencesGroup()
        prefs_page.add(toggle_group)

        for title in [
            ("Generate GTK-3.0 Theme", "Highly recommended for all users"),
            ("Generate GNOME Shell Theme", "For GNOME users"),
            ("Generate Cinnamon Theme", "For Cinnamon users"),
            ("Generate Firefox CSS Theme", "May conflict with existing theme"),
            ("Run in background", "For users who swap between light/dark mode"),
        ]:
            if title[0] == "Generate GTK-3.0 Theme":
                state = win.modify_gtk3_theme

                def state_function(value):
                    win.modify_gtk3_theme = value
            elif title[0] == "Generate GNOME Shell Theme":
                state = win.modify_gnome_shell

                def state_function(value):
                    win.modify_gnome_shell = value
            elif title[0] == "Generate Cinnamon Theme":
                state = win.modify_cinnamon_shell

                def state_function(value):
                    win.modify_cinnamon_shell = value
            elif title[0] == "Generate Firefox CSS Theme":
                state = win.firefox_theme

                def state_function(value):
                    win.firefox_theme = value
            else:
                state = win.run_in_background

                def state_function(value):
                    win.run_in_background = value

            row = Adw.SwitchRow(title=_(title[0]), subtitle=_(title[1]), active=state)
            row.connect(
                "notify::active",
                self.on_pref_toggle_switched,
                title[0],
                win,
                state_function,
            )
            toggle_group.add(row)

        self.append(prefs_page)

    def on_pref_toggle_switched(self, switch, _pspec, title, win, state_function):
        state = switch.get_active()
        state_function(state)
        win.save_prefs()
        if title == "Generate GTK-3.0 Theme":
            if not state:
                # Only remove Rewaita-managed files — never wipe the whole
                # ~/.config/gtk-3.0 directory (it can contain Nautilus bookmarks,
                # settings.ini, and other user data). See issue #147.
                self.clear_rewaita_gtk_files("gtk-3.0")
                open_toast(
                    win,
                    _(
                        "GTK-3.0 theme generation disabled. Bookmarks and other data were preserved."
                    ),
                )
            else:
                win.on_theme_selected()
        elif title == "Generate GNOME Shell Theme":
            self.clear_gnome_shell(state, win)
            if not state:
                open_toast(win, _("GNOME Shell theme generation disabled."))
        elif title == "Run in background":
            change_autostart(state)
            if state:
                open_toast(
                    win, _("Background mode enabled. Rewaita will start automatically.")
                )
            else:
                open_toast(win, _("Background mode disabled."))
        else:
            win.on_theme_selected()

    def clear_rewaita_gtk_files(self, folder):
        """Remove only Rewaita-owned CSS files from a GTK config folder.

        Never delete unrelated files such as Nautilus bookmarks or settings.ini.
        """
        folder_path = os.path.join(GLib.getenv("HOME"), ".config", folder)
        if not os.path.isdir(folder_path):
            return

        for name in ("rewaita.css",):
            path = os.path.join(folder_path, name)
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.unlink(path)
            except Exception as e:
                print(f"Failed to remove {path}: {e}")

        # Strip the @import line from gtk.css if present, without deleting the file
        gtk_css = os.path.join(folder_path, "gtk.css")
        if os.path.isfile(gtk_css) and not os.path.islink(gtk_css):
            try:
                with open(gtk_css, "r") as f:
                    lines = f.readlines()
                new_lines = [
                    line
                    for line in lines
                    if '@import "rewaita.css"' not in line
                    and "@import 'rewaita.css'" not in line
                ]
                if len(new_lines) != len(lines):
                    with open(gtk_css, "w") as f:
                        f.writelines(new_lines)
            except Exception as e:
                print(f"Failed to clean gtk.css import: {e}")

    def clear_gnome_shell(self, state, win):
        from .window import reset_gnome_shell as reset_shell

        if not state:
            folder_path = os.path.join(
                GLib.getenv("HOME"),
                ".local",
                "share",
                "themes",
                "rewaita",
                "gnome-shell",
            )
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                reset_shell()
        else:
            win.on_theme_selected()
