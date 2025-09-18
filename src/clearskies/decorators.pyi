# decorators.pyi
from typing import Any, Callable, TypeVar

# A TypeVar is used to say "whatever kind of function comes in,
# the same kind of function goes out."
_F = TypeVar("_F", bound=Callable[..., Any])

# This is the type signature for your decorator.
# It tells Pylance that it preserves the signature of the function it wraps.
def parameters_to_properties(wrapped: _F) -> _F: ...
