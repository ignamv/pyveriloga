from customdict import CustomDict


class Dummy:
    def __init__(self, a):
        self.a = a


def test_customdict():
    d = CustomDict(key=lambda x: x % 2)
    d[1] = 2
    assert d[1] == 2
    assert d[3] == 2
    assert 0 not in d
    assert 2 not in d
    assert list(d.values()) == [2]
    d[0] = 5
    assert list(d.values()) == [2, 5]
    d = CustomDict(key=lambda x: id(x))
    key = Dummy(2)
    d[key] = 4
    assert d[key] == 4
    assert Dummy(2) not in d
    assert list(d.values()) == [4]
