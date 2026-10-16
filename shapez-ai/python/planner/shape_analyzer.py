"""
Shape code analyzer and transformer for Shapez AI.
Author: QXIK_mIJ
License: Apache License 2.0
"""

from typing import List, Tuple, Dict, Any, Optional

SUB_SHAPES = {"C": "Circle", "R": "Rectangle", "S": "Star", "W": "Windmill", "-": "Empty"}
COLORS = {
    "u": "Uncolored", "r": "Red", "g": "Green", "b": "Blue",
    "y": "Yellow", "p": "Purple", "c": "Cyan", "w": "White", "-": "Empty"
}

class Quadrant:
    def __init__(self, shape: str = "-", color: str = "-"):
        self.shape = shape
        self.color = color

    @property
    def is_empty(self) -> bool:
        return self.shape == "-"

    def to_code(self) -> str:
        return f"{self.shape}{self.color}"

    def __repr__(self):
        return self.to_code()

class ShapeLayer:
    def __init__(self, quadrants: Optional[List[Quadrant]] = None):
        # Quadrants order: 0: TR (Top-Right), 1: BR (Bottom-Right), 2: BL (Bottom-Left), 3: TL (Top-Left)
        self.quadrants = quadrants or [Quadrant() for _ in range(4)]

    @classmethod
    def from_string(cls, code: str) -> "ShapeLayer":
        if len(code) != 8:
            raise ValueError(f"Invalid layer code length: '{code}'")
        quads = []
        for i in range(0, 8, 2):
            quads.append(Quadrant(code[i], code[i+1]))
        return cls(quads)

    def to_code(self) -> str:
        return "".join(q.to_code() for q in self.quadrants)

    def rotate_cw(self) -> "ShapeLayer":
        # Clockwise rotation shifts: TL -> TR, TR -> BR, BR -> BL, BL -> TL
        # indices: new[0]=old[3], new[1]=old[0], new[2]=old[1], new[3]=old[2]
        new_quads = [self.quadrants[3], self.quadrants[0], self.quadrants[1], self.quadrants[2]]
        return ShapeLayer(new_quads)

    def rotate_ccw(self) -> "ShapeLayer":
        new_quads = [self.quadrants[1], self.quadrants[2], self.quadrants[3], self.quadrants[0]]
        return ShapeLayer(new_quads)

    def rotate_180(self) -> "ShapeLayer":
        new_quads = [self.quadrants[2], self.quadrants[3], self.quadrants[0], self.quadrants[1]]
        return ShapeLayer(new_quads)

    def cut_half(self) -> Tuple["ShapeLayer", "ShapeLayer"]:
        # Cutter cuts vertically into Left half (BL, TL) and Right half (TR, BR)
        # Left output keeps Left half (BL, TL), empties Right half:
        left_layer = ShapeLayer([Quadrant(), Quadrant(), self.quadrants[2], self.quadrants[3]])
        # Right output keeps Right half (TR, BR), empties Left half:
        right_layer = ShapeLayer([self.quadrants[0], self.quadrants[1], Quadrant(), Quadrant()])
        return left_layer, right_layer

    @property
    def is_empty(self) -> bool:
        return all(q.is_empty for q in self.quadrants)

class ParsedShape:
    def __init__(self, layers: List[ShapeLayer]):
        self.layers = layers

    @classmethod
    def from_code(cls, code: str) -> "ParsedShape":
        if not code:
            return cls([])
        parts = code.split(":")
        layers = [ShapeLayer.from_string(p) for p in parts]
        return cls(layers)

    def to_code(self) -> str:
        return ":".join(l.to_code() for l in self.layers)

    @property
    def num_layers(self) -> int:
        return len(self.layers)

    def is_pure_raw(self) -> bool:
        """Returns True if the shape is a single unmanipulated layer of 4 uncolored, identical quadrants."""
        if len(self.layers) != 1:
            return False
        q0 = self.layers[0].quadrants[0]
        if q0.is_empty:
            return False
        # In Shapez, natural raw shapes from resource patches are strictly uncolored ('u')
        return all(q.shape == q0.shape and q.color == "u" for q in self.layers[0].quadrants)

    def describe(self) -> str:
        res = []
        for idx, l in enumerate(self.layers):
            q_desc = [f"Q{i+1}:{SUB_SHAPES.get(q.shape, q.shape)}-{COLORS.get(q.color, q.color)}" for i, q in enumerate(l.quadrants)]
            res.append(f"Layer {idx+1}: " + ", ".join(q_desc))
        return "\n".join(res)

COLOR_CODE_TO_NAME = {
    "r": "red",
    "g": "green",
    "b": "blue",
    "y": "yellow",
    "p": "purple",
    "c": "cyan",
    "w": "white",
}

COLOR_MIX_RECIPES = {
    "purple": ("red", "blue"),
    "yellow": ("red", "green"),
    "cyan": ("green", "blue"),
}

class ProductionRequirement:
    def __init__(
        self,
        op_type: str,
        raw_shape: str,
        keep_half: Optional[int] = None,
        rotation: int = 0,
        color: Optional[str] = None,
        color_mix: Optional[Tuple[str, str]] = None
    ):
        self.op_type = op_type  # "raw", "cut", "paint", "mix_and_paint", "cut_and_paint"
        self.raw_shape = raw_shape
        self.keep_half = keep_half  # 0: left half, 1: right half
        self.rotation = rotation
        self.color = color  # "red", "green", "blue", etc.
        self.color_mix = color_mix

def analyze_target_goal(target_code: str) -> ProductionRequirement:
    """Analyzes a target shape code and determines whether it can be mined directly or requires processing."""
    parsed = ParsedShape.from_code(target_code)
    if parsed.is_pure_raw():
        return ProductionRequirement(op_type="raw", raw_shape=target_code)

    # Check if target is a single-layer shape with uniform color across non-empty quadrants (e.g. cut & painted 'RbRb----')
    if len(parsed.layers) == 1:
        layer = parsed.layers[0]
        non_empty = [q for q in layer.quadrants if not q.is_empty]
        if non_empty and all(q.shape == non_empty[0].shape and q.color == non_empty[0].color for q in non_empty):
            color_code = non_empty[0].color
            if color_code != "u" and color_code in COLOR_CODE_TO_NAME:
                color_name = COLOR_CODE_TO_NAME[color_code]
                # If all 4 quadrants are present, it is pure paint (direct or mixed)
                if len(non_empty) == 4:
                    base_raw = f"{non_empty[0].shape}u{non_empty[0].shape}u{non_empty[0].shape}u{non_empty[0].shape}u"
                    if color_name in COLOR_MIX_RECIPES:
                        return ProductionRequirement(
                            op_type="mix_and_paint",
                            raw_shape=base_raw,
                            color=color_name,
                            color_mix=COLOR_MIX_RECIPES[color_name]
                        )
                    return ProductionRequirement(op_type="paint", raw_shape=base_raw, color=color_name)

                # Otherwise it has empty quadrants - test uncolored version against cutter operations
                uncolored_layer = ShapeLayer([
                    Quadrant(q.shape, "u") if not q.is_empty else Quadrant()
                    for q in layer.quadrants
                ])
                uncolored_code = uncolored_layer.to_code()

                raw_candidates = ["CuCuCuCu", "RuRuRuRu", "SuSuSuSu", "WuWuWuWu"]
                for raw in raw_candidates:
                    rl = ShapeLayer.from_string(raw)
                    left, right = rl.cut_half()

                    if uncolored_code == left.to_code():
                        return ProductionRequirement(op_type="cut_and_paint", raw_shape=raw, color=color_name, keep_half=0, rotation=0)
                    if uncolored_code == right.to_code():
                        return ProductionRequirement(op_type="cut_and_paint", raw_shape=raw, color=color_name, keep_half=1, rotation=0)

                    if uncolored_code == left.rotate_cw().to_code():
                        return ProductionRequirement(op_type="cut_and_paint", raw_shape=raw, color=color_name, keep_half=0, rotation=90)
                    if uncolored_code == right.rotate_cw().to_code():
                        return ProductionRequirement(op_type="cut_and_paint", raw_shape=raw, color=color_name, keep_half=1, rotation=90)

                    if uncolored_code == left.rotate_180().to_code():
                        return ProductionRequirement(op_type="cut_and_paint", raw_shape=raw, color=color_name, keep_half=0, rotation=180)
                    if uncolored_code == right.rotate_180().to_code():
                        return ProductionRequirement(op_type="cut_and_paint", raw_shape=raw, color=color_name, keep_half=1, rotation=180)

                    if uncolored_code == left.rotate_ccw().to_code():
                        return ProductionRequirement(op_type="cut_and_paint", raw_shape=raw, color=color_name, keep_half=0, rotation=270)
                    if uncolored_code == right.rotate_ccw().to_code():
                        return ProductionRequirement(op_type="cut_and_paint", raw_shape=raw, color=color_name, keep_half=1, rotation=270)

    raw_candidates = ["CuCuCuCu", "RuRuRuRu", "SuSuSuSu", "WuWuWuWu"]
    for raw in raw_candidates:
        layer = ShapeLayer.from_string(raw)
        left, right = layer.cut_half()

        # Direct cut (no rotation)
        if target_code == left.to_code():
            return ProductionRequirement(op_type="cut", raw_shape=raw, keep_half=0, rotation=0)
        if target_code == right.to_code():
            return ProductionRequirement(op_type="cut", raw_shape=raw, keep_half=1, rotation=0)

        # Cut + 90 deg Clockwise rotation
        if target_code == left.rotate_cw().to_code():
            return ProductionRequirement(op_type="cut", raw_shape=raw, keep_half=0, rotation=90)
        if target_code == right.rotate_cw().to_code():
            return ProductionRequirement(op_type="cut", raw_shape=raw, keep_half=1, rotation=90)

        # Cut + 180 deg rotation
        if target_code == left.rotate_180().to_code():
            return ProductionRequirement(op_type="cut", raw_shape=raw, keep_half=0, rotation=180)
        if target_code == right.rotate_180().to_code():
            return ProductionRequirement(op_type="cut", raw_shape=raw, keep_half=1, rotation=180)

        # Cut + 270 deg (CCW) rotation
        if target_code == left.rotate_ccw().to_code():
            return ProductionRequirement(op_type="cut", raw_shape=raw, keep_half=0, rotation=270)
        if target_code == right.rotate_ccw().to_code():
            return ProductionRequirement(op_type="cut", raw_shape=raw, keep_half=1, rotation=270)

    return ProductionRequirement(op_type="raw", raw_shape=target_code)


