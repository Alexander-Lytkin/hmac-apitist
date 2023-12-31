import sys
from typing import (
    Dict,
    FrozenSet,
    Mapping,
    MutableSequence,
    MutableSet,
    Sequence,
    Tuple,
    List,
)

version_info = sys.version_info[0:3]
is_py37 = version_info[:2] == (3, 7)
is_py38 = version_info[:2] == (3, 8)


def is_attrs_class(cls):
    return getattr(cls, "__attrs_attrs__", None) is not None


def has_args(cls):
    return getattr(cls, "__args__", None) is not None


def _subclass(typ):
    """ a shortcut """
    return lambda cls: issubclass(cls, typ)


if is_py37 or is_py38:
    from typing import Union, _GenericAlias


    def is_union_type(obj):
        return (
                obj is Union
                or isinstance(obj, _GenericAlias)
                and obj.__origin__ is Union
        )


    def is_sequence(type):
        return (
                type is List
                or type.__class__ is _GenericAlias
                and issubclass(type.__origin__, Sequence)
        )


    def is_frozenset(type):
        return type.__class__ is _GenericAlias and issubclass(
            type.__origin__, FrozenSet
        )


    def is_mutable_set(type):
        return type.__class__ is _GenericAlias and issubclass(
            type.__origin__, MutableSet
        )


    def is_tuple(type):
        return type is Tuple or (
                type.__class__ is _GenericAlias
                and issubclass(type.__origin__, Tuple)
        )


    def is_mapping(type):
        return type is Mapping or (
                type.__class__ is _GenericAlias
                and issubclass(type.__origin__, Mapping)
        )


    bare_list_args = List.__args__
    bare_seq_args = Sequence.__args__
    bare_mapping_args = Mapping.__args__
    bare_dict_args = Dict.__args__
    bare_mutable_seq_args = MutableSequence.__args__


    def is_bare(type):
        args = type.__args__
        return (
                args == bare_list_args
                or args == bare_seq_args
                or args == bare_mapping_args
                or args == bare_dict_args
                or args == bare_mutable_seq_args
        )


else:
    # 3.9+
    from typing import (
        Union,
        _GenericAlias,
        _UnionGenericAlias,
    )


    def is_union_type(obj):
        """Return true if the object is a union. """
        return (
                obj is Union
                or isinstance(obj, _UnionGenericAlias)
                and obj.__origin__ is Union
        )


    def is_frozenset(type):
        return issubclass(type, FrozenSet)


    def is_mutable_set(type):
        return issubclass(type, MutableSet)


    def is_sequence(type):
        return (
                type in (List, list, Sequence, MutableSequence)
                or (
                        type.__class__ is _GenericAlias
                        and issubclass(type.__origin__, Sequence)
                )
                or (getattr(type, "__origin__", None) is list)
        )


    def is_tuple(type):
        return (
                type in (Tuple, tuple)
                or (
                        type.__class__ is _GenericAlias
                        and issubclass(type.__origin__, Tuple)
                )
                or (getattr(type, "__origin__", None) is tuple)
        )


    def is_mapping(type):
        return issubclass(type, Mapping)
