import bpy
from bpy.types import Context
from functools import wraps
import inspect


def default_context(fn):
    "NOTE does not work with kind = VAR_POSITIONAL parameters"
    sig = inspect.signature(fn)
    context_param = next(
        name
        for name, param in sig.parameters.items()
        if issubclass(param.annotation, Context)
    )

    @wraps(fn)
    def wrapper(*args, **kwargs):
        args = {name: value for name, value in zip(sig.parameters, args)}
        kwargs.update(args)
        if context_param not in kwargs:
            kwargs[context_param] = bpy.context
        return fn(**kwargs)

    return wrapper
