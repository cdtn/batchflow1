""" Contains classes to handle batch data components """


class ComponentDescriptor:
    """ Class for handling one component item """
    def __init__(self, component):
        self._component = component
        self._default = None

    def __get__(self, instance, cls):
        if instance.data is None:
            return self._default
        elif instance.pos is None:
            return instance.data[self._component]
        else:
            pos = instance.pos[self._component]
            return instance.data[self._component][pos]

    def __set__(self, instance, value):
        if instance._pos is None:
            new_data = list(instance.data) if instance.data is not None else list()
            new_data[self._component] = value
            instance._data = tuple(new_data)
        else:
            pos = instance.pos[self._component]
            instance.data[self._component][pos] = value


class BaseComponentsTuple:
    """ Base class for a component tuple """
    components = None
    def __init__(self, data=None, pos=None):
        self.data = data
        if pos is not None and not isinstance(pos, list):
            pos = [pos for _ in self.components]
        self.pos = pos


class MetaComponentsTuple(type):
    """ Class factory for a component tuple """
    def __init__(cls, *args, **kwargs):
        _ = kwargs
        super().__init__(*args)

    def __new__(mcs, name, components):
        comp_class = super().__new__(mcs, name, (BaseComponentsTuple,), {})
        comp_class.components = components
        for i, cmp in enumerate(components):
            setattr(comp_class, cmp, ComponentDescriptor(i))
        return comp_class
