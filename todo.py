def __repr__(self):
    return "<%s '%s', handle %x at %#x>" % \
           (self.__class__.__name__, self._name,
            (self._handle & (_sys.maxsize * 2 + 1)),
            id(self) & (_sys.maxsize * 2 + 1))


def __getattr__(self, name):
    if name.startswith('__') and name.endswith('__'):
        raise AttributeError(name)
    func = self.__getitem__(name)
    setattr(self, name, func)
    return func


def __getitem__(self, name_or_ordinal):
    func = self._FuncPtr((name_or_ordinal, self))
    if not isinstance(name_or_ordinal, int):
        func.__name__ = name_or_ordinal
    return func

import json
li={{'a':[1,2,3]},{'b':[4,5,6]}}
print(type(json.dumps(li)))
