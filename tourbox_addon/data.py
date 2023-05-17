import pickle
import base64
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

import bpy
from bpy.types import AddonPreferences, Brush
from bpy.props import StringProperty


@dataclass(slots=True)
class Store:
    @staticmethod
    def make_brush_name(mode: str, button: str):
        return f"{button}{mode}Brush"

    def get_brush(self, mode: str, button: str):
        return bpy.data.brushes.get(Store.make_brush_name(mode, button), None)

    def overwrite_brush(self, mode: str, button: str, brush: Brush) -> Brush:
        oldbrush = self.get_brush(mode, button)
        if oldbrush is not None:
            if oldbrush.name == brush.name:
                return oldbrush
            bpy.data.brushes.remove(oldbrush)
        brush = brush.copy()
        brush.name = Store.make_brush_name(mode, button)
        return brush


__store: Store | None = None


def derialize(data: str) -> tuple:
    return pickle.loads(base64.b64decode(data.encode()))


def serialize(data: tuple) -> str:
    return base64.b64encode(pickle.dumps(data)).decode("ascii")


class AddonTourboxPreferences(AddonPreferences):
    bl_idname = __package__

    storage: StringProperty(
        name="Persistent Storage",
        description="Stores the addon configuration",
        default=serialize(Store()),
    )


@contextmanager
def modify_store() -> Iterator[Store]:
    global __store
    prefs = bpy.context.preferences.addons[__package__].preferences
    if __store is None:
        __store = derialize(prefs.storage)
    try:
        yield __store
    except Exception as e:
        __store = derialize(prefs.storage)
        raise e
    prefs.storage = serialize(__store)
