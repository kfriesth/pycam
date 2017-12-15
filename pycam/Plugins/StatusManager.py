# -*- coding: utf-8 -*-
"""
Copyright 2011 Lars Kruse <devel@sumpfralle.de>

This file is part of PyCAM.

PyCAM is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyCAM is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyCAM.  If not, see <http://www.gnu.org/licenses/>.
"""

import os

from pycam import FILTER_CONFIG
import pycam.Plugins
import pycam.Utils.log

_log = pycam.Utils.log.get_logger()


class StatusManager(pycam.Plugins.PluginBase):

    CATEGORIES = ["System"]

    def setup(self):
        if self.gui:
            # autoload task settings file on startup
            autoload_enable = self.gui.get_object("AutoLoadTaskFile")
            autoload_box = self.gui.get_object("StartupTaskFileBox")
            autoload_source = self.gui.get_object("StartupTaskFile")
            # TODO: fix the extension filter
#           for one_filter in get_filters_from_list(FILTER_CONFIG):
#               autoload_source.add_filter(one_filter)
#               autoload_source.set_filter(one_filter)

            def get_autoload_task_file(autoload_source=autoload_source):
                if autoload_enable.get_active():
                    return autoload_source.get_filename()
                else:
                    return ""

            def set_autoload_task_file(filename):
                if filename:
                    autoload_enable.set_active(True)
                    autoload_box.show()
                    autoload_source.set_filename(filename)
                else:
                    autoload_enable.set_active(False)
                    autoload_box.hide()
                    autoload_source.unselect_all()

            def autoload_enable_switched(widget, box):
                if not widget.get_active():
                    set_autoload_task_file(None)
                else:
                    autoload_box.show()

            autoload_enable.connect("toggled", autoload_enable_switched, autoload_box)
            self.core.settings.add_item("default_task_settings_file", get_autoload_task_file,
                                        set_autoload_task_file)
            autoload_task_filename = self.core.settings.get("default_task_settings_file")
            # TODO: use "startup" hook instead
            if autoload_task_filename:
                self.open_task_settings_file(autoload_task_filename)
            self._gtk_handlers = []
            for objname, callback, data, accel_key in (
                    ("LoadProjectSettings", self.load_task_settings_file, None, "<Control>t"),
                    ("SaveProjectSettings", self.save_task_settings_file,
                     lambda: self.last_task_settings_uri, None),
                    ("SaveAsProjectSettings", self.save_task_settings_file, None, None)):
                obj = self.gui.get_object(objname)
                self.register_gtk_accelerator("status_manager", obj, accel_key, objname)
                self._gtk_handlers.append((obj, "activate", callback))
            self.register_gtk_handlers(self._gtk_handlers)
        return True

    def teardown(self):
        if self.gui:
            self.unregister_gtk_handlers(self._gtk_handlers)

    def open_task_settings_file(self, filename):
        """ This function is used by the commandline handler """
        self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        self.load_task_settings_file(filename=filename)

    def load_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not filename:
            filename = self.core.settings.get("get_filename_func")("Loading settings ...",
                                                                   mode_load=True,
                                                                   type_filter=FILTER_CONFIG)
            # Only update the last_task_settings attribute if the task file was
            # loaded interactively. E.g. ignore the initial task file loading.
            if filename:
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        if filename:
            _log.info("Loading task settings file: %s", str(filename))
            self.load_task_settings(filename)
            self.core.emit_event("notify-file-opened", filename)

    def save_task_settings_file(self, widget=None, filename=None):
        if callable(filename):
            filename = filename()
        if not hasattr(filename, "split") and not isinstance(filename, pycam.Utils.URIHandler):
            # we open a dialog
            filename = self.core.settings.get("get_filename_func")(
                "Save settings to ...", mode_load=False, type_filter=FILTER_CONFIG,
                filename_templates=(self.last_task_settings_uri, self.core.last_model_uri))
            if filename:
                self.last_task_settings_uri = pycam.Utils.URIHandler(filename)
        # no filename given -> exit
        if not filename:
            return
        settings = self.dump_state()
        try:
            out_file = open(filename, "w")
            out_file.write(settings)
            out_file.close()
            _log.info("Project settings written to %s", filename)
            self.core.emit_event("notify-file-opened", filename)
        except IOError:
            _log.error("Failed to save settings file")

    def load_task_settings(self, filename=None):
        settings = pycam.Gui.Settings.ProcessSettings()
        if filename is not None:
            settings.load_file(filename)
        # flush all tables (without re-assigning new objects)
        for one_list_name in ("tools", "processes", "bounds", "tasks"):
            one_list = self.core.settings.get(one_list_name)
            while one_list:
                one_list.pop()
        # TODO: load default tools/processes/bounds
