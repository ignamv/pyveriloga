from collections.abc import MutableMapping


class CustomDict(MutableMapping):
    def __init__(self, key, items=None):
        self.keyfunc = key
        self._items = {}
        self._keys = {}
        if items is not None:
            for key, value in dict(items):
                self._items[id(key)] = value
                self._keys[id(key)] = key

    def __getitem__(self, key):
        return self._items[self.keyfunc(key)]

    def __setitem__(self, key, value):
        self._items[self.keyfunc(key)] = value
        self._keys[self.keyfunc(key)] = key

    def __delitem__(self, key):
        del self._items[self.keyfunc(key)]
        del self._keys[self.keyfunc(key)]

    def __iter__(self):
        return self.keys()

    def __len__(self):
        return len(self._items)

    def values(self):
        return self._items.values()

    def items(self):
        return ((self._keys[id_], value) for id_, value in self._items.items())

    def keys(self):
        return self._keys.values()
