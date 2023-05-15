from bpy.types import Context, Paint, Brush
from tourbox_addon.data import modify_store

from tourbox_addon.util import default_context


@default_context
def get_paint(ctx: Context) -> Paint:
    match ctx.mode:
        case "SCULPT_CURVES":
            return ctx.tool_settings.curves_sculpt
        case "PAINT_GPENCIL":
            return ctx.tool_settings.gpencil_paint
        case "SCULPT_GPENCIL":
            return ctx.tool_settings.gpencil_sculpt
        case "VERTEX_GPENCIL":
            return ctx.tool_settings.gpencil_vertex_paint
        case "WEIGHT_GPENCIL":
            return ctx.tool_settings.gpencil_weight_paint
        case "PAINT_TEXTURE":
            return ctx.tool_settings.image_paint
        case "SCULPT":
            return ctx.tool_settings.sculpt
        case "EDIT_MESH":
            return ctx.tool_settings.uv_sculpt
        case "PAINT_VERTEX":
            return ctx.tool_settings.vertex_paint
        case "PAINT_WEIGHT":
            return ctx.tool_settings.weight_paint


@default_context
def get_active_brush(ctx: Context) -> Brush:
    return get_paint(ctx).brush


@default_context
def set_active_brush(ctx: Context, brush: Brush):
    get_paint(ctx).brush = brush


@default_context
def set_active_brush_size(ctx: Context, size: int) -> int:
    """
    Change the current size (radius) of the active brush.
    Takes whether unified radius setting is enabled and will clamp
    the radius between the allowed values (1 and 5000)
    the clamped value is returned
    """
    settings = ctx.tool_settings.unified_paint_settings
    target = settings if settings.use_unified_size else get_active_brush(ctx)
    target.size = max(1, min(5000, size))
    return target.size


@default_context
def set_active_brush_strength(ctx: Context, strength: float) -> float:
    """
    Similar to set_active_brush_size but for brush strength
    Note that unified strength in Blender is bugged currently
    """
    settings = ctx.tool_settings.unified_paint_settings
    target = settings if settings.use_unified_strength else get_active_brush(ctx)
    target.size = max(0, min(10, strength))
    return target.size


@default_context
def bind_active_brush_button(ctx: Context, button: str):
    brush = get_active_brush()
    with modify_store() as store:
        newbrush = store.overwrite_brush(ctx.mode, button, brush)
    set_active_brush(newbrush)
