from collections.abc import MutableMapping


class CustomDict(MutableMapping):
    def __init__(self, key, items=None):
        self.keyfunc = key
        if items is None:
            self.items = {}
        else:
            self.items = dict(items)

    def __getitem__(self, key):
        return self.items[self.keyfunc(key)]

    def __setitem__(self, key, value):
        self.items[self.keyfunc(key)] = value

    def __delitem__(self, key):
        del self.items[self.keyfunc(key)]

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def values(self):
        return self.items.values()
