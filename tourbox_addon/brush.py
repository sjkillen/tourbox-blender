from typing import Annotated, Any, get_type_hints
from bpy.types import Context, Paint, Brush
from tourbox_addon.util import default_context


SCULPT_BRUSH_DIRECTIONS = {
    "ADD": "SUBTRACT",
    "INFLATE": "DEFLATE",
    "CONTRAST": "FLATTEN",
    "SMOOTH": "ENHANCE_DETAILS",
    "FILL": "DEEPEN",
    "SCRAPE": "PEAKS",
    "MAGNIFY": "PINCH",
}
SCULPT_BRUSH_DIRECTIONS_INV = {
    value: key for key, value in SCULPT_BRUSH_DIRECTIONS.items()
}

unified_fields = {
    "strength": "use_unified_strength",
    "size": "use_unified_size",
    "color": "use_unified_color",
}


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
def get_active_brush_size(ctx: Context) -> int:
    return set_active_brush_size(ctx, -1)


@default_context
def set_active_brush_strength(ctx: Context, strength: float | None) -> float:
    """
    Similar to set_active_brush_size but for brush strength
    Note that unified strength in Blender is bugged currently
    """
    settings = ctx.tool_settings.unified_paint_settings
    target = settings if settings.use_unified_strength else get_active_brush(ctx)
    if strength in range(0, 10):
        target.size = max(0, min(10, strength))
    return target.size


@default_context
def get_active_brush_strength(ctx: Context) -> float:
    return set_active_brush_strength(ctx, -1.0)


@default_context
def set_active_brush_flow(ctx: Context, flow: float) -> float:
    brush = get_active_brush(ctx)
    brush.flow = max(0.0, min(1.0, flow))
    return brush.flow


@default_context
def get_active_brush_flow(ctx: Context) -> float:
    return set_active_brush_flow(ctx, -1.0)


class ActiveBrush:
    # lowerbound, upperbound, use_unified
    strength: Annotated[float, 0.0, 10.0]
    size: Annotated[int, 1, 5000]
    flow: Annotated[float, 0.0, 1.0]
    direction: bool

    @default_context
    def __init__(self, ctx: Context) -> None:
        object.__setattr__(self, "ctx", ctx)

    def direction_get(self) -> bool:
        brush = get_active_brush(self.ctx)
        if brush.direction in SCULPT_BRUSH_DIRECTIONS:
            return 1
        else:
            assert brush.direction in SCULPT_BRUSH_DIRECTIONS_INV
            return 0

    def direction_set(self, v: int):
        brush = get_active_brush(self.ctx)
        assert v in range(0, 2)
        if self.direction_get() == 0:
            brush.direction = SCULPT_BRUSH_DIRECTIONS_INV[brush.direction]
        else:
            brush.direction = SCULPT_BRUSH_DIRECTIONS[brush.direction]

    def __getattr__(self, field: str):
        # TODO can't get property's to work right with getattr/setattr
        if field == "direction":
            return self.direction_get()
        return self.__access(field, None)

    def __setattr__(self, field: str, value):
        # TODO can't get property's to work right with getattr/setattr
        if field == "direction":
            return self.direction_set(value)
        self.__access(field, value)

    def __access(self, field: str, value):
        lowerbound, upperbound = ActiveBrush.__annotations__[field].__metadata__
        settings = self.ctx.tool_settings.unified_paint_settings
        target = (
            settings
            if field in unified_fields and getattr(settings, unified_fields[field])
            else get_active_brush(self.ctx)
        )
        if value is not None:
            value = max(lowerbound, min(upperbound, value))
            setattr(target, field, value)
        return getattr(target, field)
