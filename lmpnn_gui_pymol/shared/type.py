from typing import Any, cast, Optional, Type

class TypeChecks:
    """
    Python's reflection is full of quirks. This class tries to
    capture all those quirks and expose functions around them.
    """

    @classmethod
    def is_named_tuple(cls, ty: Type):

        return issubclass(ty, tuple) \
            and hasattr(ty, '_fields') \
            and all(isinstance(f, str) for f in getattr(ty, '_fields'))

    @classmethod
    def get_generic_list_type(cls, ty: Type) -> Optional[Type]:

        if ty == list:
            return cast(Type, Any)

        base = getattr(ty, '__origin__', None)

        if base is None:
            return None

        if base == list:
            return ty.__args__[0]
        else:
            return None

    @classmethod
    def is_list(cls, ty: Type) -> bool:
        return ty == list or getattr(ty, '__origin__', None) == list

    @classmethod
    def is_any(cls, ty: Type) -> bool:
        return ty == Any



