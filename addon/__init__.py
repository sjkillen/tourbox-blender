# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "tourbox-controller",
    "author": ".",
    "description": "",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic",
}

from functools import partial
from os import kill
from signal import SIGINT
from subprocess import Popen, PIPE
from threading import Thread
from typing import IO

import bpy
from bpy.types import Brush

EXE = "/home/squirrel/tourbox-blender/target/debug/tbelite"

known_modes = ("SCULPT",)
supported_events = ("MouseWheelUp", "MouseWheelDown")


def on_input_event(event: str):
    mode = bpy.context.mode
    if mode not in known_modes:
        return
    print(event)
    match event:
        case "MouseWheelUp":
            cycle_mode_brush(mode, -1)
        case "MouseWheelDown":
            cycle_mode_brush(mode, 1)


def thread_entry(file: IO):
    while True:
        data = file.readline().decode("utf-8").strip()
        if data in supported_events:
            # Hack to get back to a "safe" blender thread, hopefully. But nothing is certain
            bpy.app.timers.register(partial(on_input_event, data), first_interval=0)


def set_mode_brush(mode: str, brush: Brush):
    if mode == "SCULPT":
        bpy.context.tool_settings.sculpt.brush = brush
    else:
        raise Exception(f"Unknown Mode: {mode}")


def get_mode_active_brush(mode: str):
    if mode == "SCULPT":
        return bpy.context.tool_settings.sculpt.brush
    raise Exception(f"Unknown Mode: {mode}")


def get_mode_brushes(mode: str):
    if mode == "SCULPT":
        return (brush for brush in bpy.data.brushes if brush.use_paint_sculpt)
    raise Exception(f"Unknown Mode: {mode}")


def get_active_tool():
    return bpy.context.workspace.tools.from_space_view3d_mode(
        bpy.context.mode, create=False
    ).idname


def lookup_brush(mode: str, brush_name: str) -> str | None:
    return next(
        (brush for brush in get_mode_brushes(mode) if brush.name == brush_name), None
    )

class MissingBrush(Exception):
    pass

def tool_to_brush(mode: str, toollabel: str):
    """Hackily convert tool label to brushname
    The tools have an operator associated with them to switch to the correct brush, but they raise errors when called here
    """
    brush = lookup_brush(mode, toollabel)
    if brush is not None:
        return brush
    if mode == "SCULPT":
        mode_label = f"Sculpt{toollabel}"
    else:
        raise Exception(f"Unknown Mode: {mode}")
    brush = lookup_brush(mode, mode_label)
    if brush is not None:
        return brush
    for suffix in ("/Deflate", "/Contrast", "/Deepen","/Peaks","/Magnify"):
        brush = lookup_brush(mode, f"{toollabel}{suffix}")
        if brush is not None:
            return brush
    raise MissingBrush(f"Failed to convert tool '{toollabel}' to a brush")


def get_tools():
    return tuple(
        (tool.idname, tool.label)
        for tool in bpy.types.VIEW3D_PT_tools_active.tools_from_context(bpy.context)
        if hasattr(tool, "idname")
    )


def cycle_mode_brush(mode: str, delta: int):
    "This function barely works, but it works enough"
    if mode not in known_modes:
        return
    tool_idname = get_active_tool()
    tools = get_tools()
    idx = next(i for i, (oidname, _) in enumerate(tools) if oidname == tool_idname)
    idx += delta
    idx %= len(tools)
    try:
        brush = tool_to_brush(mode, tools[idx][1])
    except MissingBrush:
        brush = tool_to_brush(mode, tools[0][1])
    set_mode_brush(mode, brush)


daemon = None


def start_daemon():
    global daemon
    if daemon is not None:
        return
    daemon = Popen([EXE], stdout=PIPE)
    t = Thread(target=thread_entry, args=(daemon.stdout,))
    t.start()


def stop_daemon():
    global daemon
    if daemon is None:
        return
    kill(daemon.pid, SIGINT)
    daemon = None


def register():
    start_daemon()


def unregister():
    stop_daemon()
