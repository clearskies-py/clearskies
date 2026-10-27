from __future__ import annotations

import functools
import inspect


def parameters_to_properties(wrapped):
    wrapped_args = inspect.getfullargspec(wrapped)

    @functools.wraps(wrapped)
    def wrapper(*args, **kwargs):
        instance = args[0] if args else None
        if not instance:
            raise ValueError(
                "The parameters_to_properties decorator only works for methods in classes, not plain functions"
            )

        for key, value in zip(wrapped_args.args[1:], args[1:]):
            # if it's a dictionary or a list then copy it to avoid linking data
            if isinstance(value, dict):
                value = {**value}
            if isinstance(value, list):
                value = [*value]
            setattr(instance, key, value)

        for key, value in kwargs.items():
            # if it's a dictionary or a list then copy it to avoid linking data
            if isinstance(value, dict):
                value = {**value}
            if isinstance(value, list):
                value = [*value]
            setattr(instance, key, value)

        wrapped(*args, **kwargs)

    # inspect.getfullargspec (used by the DI container) ignores __wrapped__ but honours __signature__
    wrapper.__signature__ = inspect.signature(wrapped)  # ty: ignore[unresolved-attribute]
    return wrapper
