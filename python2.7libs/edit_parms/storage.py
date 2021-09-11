import json
import os

import hou

from .singleton import Singleton

STORAGE_FILE_PATH = hou.expandString('$HOUDINI_USER_PREF_DIR/editparms.data')


class Storage(object):
    __metaclass__ = Singleton

    def __init__(self):
        self._timestamp = 0
        self._data = {
            'presets': [],
            'history': {}
        }

    @property
    def data(self):
        if not os.path.isfile(STORAGE_FILE_PATH):
            return self._data

        timestamp = os.stat(STORAGE_FILE_PATH).st_mtime
        if self._timestamp != timestamp:
            try:
                with open(STORAGE_FILE_PATH) as storage_file:
                    self._data = json.load(storage_file)
                    self._timestamp = os.stat(STORAGE_FILE_PATH).st_mtime
            except IOError:
                pass  # Unsuccessful attempt - cheer up
        return self._data

    def _save(self):
        try:
            with open(STORAGE_FILE_PATH, 'w') as storage_file:
                json.dump(self._data, storage_file)
        except IOError:
            return

    @property
    def presets(self):
        return self.data.get('presets', [])

    def addPreset(self, expression):
        presets_data = self.data.setdefault('presets', [])
        if expression not in presets_data:
            presets_data.append(expression)
            self._save()

    def removePreset(self, expression):
        presets = self.data.get('presets')
        if not presets:
            return

        try:
            presets.remove(expression)
        except ValueError:
            return
        self._save()

    def setupFromHistory(self, parm_name):
        history_data = self.data.get('history')
        if not history_data:
            return None

        return history_data.get(parm_name)

    def addToHistory(self, parm_name, data):
        history_data = self.data.setdefault('history', {})
        history_data[parm_name] = data
        self._save()
