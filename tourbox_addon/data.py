from pathlib import Path
import pickle
import base64
from contextlib import contextmanager

import bpy
from bpy.types import AddonPreferences, Context
from bpy.props import StringProperty

PICKLECONFIG = str((Path.home() / ".config/tourbox-blender.pickle").resolve())

try:
    with open(PICKLECONFIG, "rb") as fo:
        SWATCHES = pickle.load(fo)
except Exception as e:
    print(e)

__store = None


def derialize(data: str) -> tuple:
    return pickle.loads(base64.decodebytes(data))


def serialize(data: tuple) -> str:
    return base64.encode(pickle.dumps(data))


class AddonTourboxPreferences(AddonPreferences):
    bl_idname = __package__

    storage: StringProperty(
        name="Use View Axes X",
        description="If enabled, the X axis is relative to the 3D viewport instead of the global axes",
        default=serialize(tuple()),
    )


@contextmanager
def modify_store():
    prefs = bpy.context.preferences.addons[__package__].preferences
    if __store is None:
        __store = derialize(prefs.storage)
    try:
        yield __store
    except Exception as e:
        __store = derialize(prefs.storage)
        raise e
    prefs.storage = serialize(__store)
