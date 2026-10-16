"""
Installed Mod Registry & Knowledge Base for Shapez AI.
Indexes all active user mods, building IDs, custom variants, and technologies.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("ShapezAI.Mods")

MODS_DIR = Path(os.path.expandvars(r"%APPDATA%\shapez.io\mods"))

class ModBuildingInfo(BaseModel):
    building_class: str
    building_id: str
    display_name: str
    description: str
    dimensions: List[int] = Field(default_factory=lambda: [1, 1])
    capabilities: List[str] = Field(default_factory=list)

class InstalledMod(BaseModel):
    id: str
    name: str
    version: str
    author: str
    description: str
    filename: str
    is_active: bool = True
    new_buildings: List[ModBuildingInfo] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)

# Comprehensive catalog of installed mods and their game additions
KNOWN_MOD_SPECS: Dict[str, Dict[str, Any]] = {
    "4 way Balancer.js": {
        "id": "add-building-basic",
        "name": "4 way Balancer",
        "version": "1.1",
        "author": "Kodi4444",
        "description": "4-wide belt balancer and distributor for high-volume belt routing.",
        "buildings": [
            ModBuildingInfo(
                building_class="MetaDemoModBuilding",
                building_id="balancer_4way",
                display_name="4-Way Balancer",
                description="Splits and evenly distributes items across 4 parallel belts.",
                dimensions=[4, 1],
                capabilities=["balance_4_lanes", "eliminate_belt_compression_imbalance"]
            )
        ],
        "features": ["4-lane even distribution", "compact high-throughput bus routing"]
    },
    "mirrored_buildings.js": {
        "id": "mirrored_buildings",
        "name": "Mirrored Buildings",
        "version": "v1.3.0",
        "author": "WaffleDevs",
        "description": "Mirrored variations of essential machines allowing symmetrical factory layouts.",
        "buildings": [
            ModBuildingInfo(
                building_class="MetaCutterMirrored",
                building_id="cutter_mirrored",
                display_name="Mirrored Cutter",
                description="Cuts shapes in half with mirrored output orientations (right side output first).",
                dimensions=[2, 1],
                capabilities=["cut_shape", "symmetric_routing"]
            ),
            ModBuildingInfo(
                building_class="MetaStackerMirrored",
                building_id="stacker_mirrored",
                display_name="Mirrored Stacker",
                description="Stacks shapes with inverted left/right input priority.",
                dimensions=[1, 1],
                capabilities=["stack_shapes_mirrored"]
            ),
            ModBuildingInfo(
                building_class="MetaMixerMirrored",
                building_id="mixer_mirrored",
                display_name="Mirrored Color Mixer",
                description="Mirrored color mixing inputs for symmetrical paint setups.",
                dimensions=[2, 1],
                capabilities=["mix_colors_mirrored"]
            ),
            ModBuildingInfo(
                building_class="MetaPainterDoubleMirrored",
                building_id="painter_double_mirrored",
                display_name="Mirrored Double Painter",
                description="Paints two shapes simultaneously with mirrored paint fluid ports.",
                dimensions=[2, 2],
                capabilities=["paint_double_mirrored"]
            )
        ],
        "features": ["perfect factory symmetry", "half-turn minimization", "parallel mirror bus routing"]
    },
    "packaging.js": {
        "id": "packaging",
        "name": "Packaging",
        "version": "1.2.3",
        "author": "zoidran",
        "description": "Allows packing multiple shape parts into crates for ultra-dense conveyor transport.",
        "buildings": [
            ModBuildingInfo(
                building_class="MetaStorageBuilding",
                building_id="packager",
                display_name="Packager / Unpackager",
                description="Packs 4 shapes into a single box crate on input; unpacks crate into 4 shapes on output.",
                dimensions=[1, 1],
                capabilities=["compress_cargo_4x", "high_density_belt_transport", "unboxing"]
            )
        ],
        "features": ["4x throughput multiplication over standard belts", "bulk crate shipping"]
    },
    "micro-filters.mod.js": {
        "id": "micro-filters",
        "name": "Micro Filters",
        "version": "1.0",
        "author": "Community",
        "description": "Compact inline shape and color filters without bulky diverter belts.",
        "buildings": [
            ModBuildingInfo(
                building_class="MetaFilterBuilding",
                building_id="micro_filter",
                display_name="Micro Inline Filter",
                description="Direct 1x1 inline filter sorting shapes by definition without side ejectors.",
                dimensions=[1, 1],
                capabilities=["inline_filtering", "filter_by_color_or_shape"]
            )
        ],
        "features": ["zero footprint filtering", "instant waste rejection"]
    },
    "sk_bldCustomStorage.js": {
        "id": "sk-custom-storage",
        "name": "Custom Storage",
        "version": "1.3.2",
        "author": "Skrip",
        "description": "Configurable buffer storage with flexible capacity limits.",
        "buildings": [
            ModBuildingInfo(
                building_class="CustomStorageBuilding",
                building_id="storage_custom",
                display_name="Configurable Buffer Storage",
                description="Stores items with customizable capacity to buffer surges in production.",
                dimensions=[2, 2],
                capabilities=["buffer_inventory", "surge_absorption"]
            )
        ],
        "features": ["production surge protection", "overflow buffer"]
    },
    "sk_bldNote.js": {
        "id": "sk-note-building",
        "name": "Note Building",
        "version": "1.2.0",
        "author": "Skrip",
        "description": "Places visual annotation notes on the map to label factory sectors.",
        "buildings": [
            ModBuildingInfo(
                building_class="NoteBuilding",
                building_id="map_note",
                display_name="Sector Annotation Note",
                description="Text label on the map indicating factory zone purpose or level goal.",
                dimensions=[1, 1],
                capabilities=["map_labeling", "visual_documentation"]
            )
        ],
        "features": ["zone labeling", "factory architecture self-documentation"]
    },
    "EdgeRotation-1.1.js": {
        "id": "edgerotation",
        "name": "Edge Rotation",
        "version": "1.1",
        "author": "BlastSlimey",
        "description": "Rotates only outer shape quadrants where adjacent slot is empty.",
        "buildings": [
            ModBuildingInfo(
                building_class="MetaEdgeRotationBuilding",
                building_id="edge_rotater",
                display_name="Edge Rotator",
                description="Rotates specific quadrant edges without rotating entire shape.",
                dimensions=[1, 1],
                capabilities=["edge_rotation", "complex_layer_geometry"]
            )
        ],
        "features": ["advanced pinwheel & asymmetric shape sculpting"]
    },
    "speedturbo _v1.js": {
        "id": "speed-turbo",
        "name": "Speed Turbo",
        "version": "1.0",
        "author": "Asynic",
        "description": "Adjusts game simulation speed multiplier (1x, 2x, 5x, 10x).",
        "features": ["simulation acceleration", "high-speed benchmarking"]
    },
    "usage_statistics.js": {
        "id": "usage-statistics",
        "name": "Usage Statistics",
        "version": "1.0",
        "author": "tobspr",
        "description": "Measures real throughput on each building and detects bottlenecks.",
        "features": ["per-building rate tracking", "real-time congestion alerts"]
    }
}

class ModRegistry:
    def __init__(self, mods_path: Optional[Path] = None):
        self.mods_path = mods_path or MODS_DIR
        self.installed_mods: Dict[str, InstalledMod] = {}
        self.scan_mods()

    def scan_mods(self):
        """Scans the disk for all installed mods and loads specifications."""
        if not self.mods_path.exists():
            logger.warning(f"Mods path does not exist: {self.mods_path}")
            return

        for fpath in self.mods_path.glob("*.js"):
            fname = fpath.name
            if fname == "shapez-ai-bridge.js":
                continue

            if fname in KNOWN_MOD_SPECS:
                spec = KNOWN_MOD_SPECS[fname]
                mod = InstalledMod(
                    id=spec["id"],
                    name=spec["name"],
                    version=spec["version"],
                    author=spec["author"],
                    description=spec["description"],
                    filename=fname,
                    new_buildings=spec.get("buildings", []),
                    features=spec.get("features", [])
                )
            else:
                mod = InstalledMod(
                    id=fpath.stem,
                    name=fpath.stem,
                    version="1.0",
                    author="Community",
                    description=f"User installed mod file: {fname}",
                    filename=fname,
                    new_buildings=[],
                    features=[]
                )
            self.installed_mods[mod.id] = mod

        logger.info(f"ModRegistry: Loaded {len(self.installed_mods)} installed mods.")

    def get_prompt_summary(self) -> str:
        """Generates a concise markdown summary of available modded buildings and capabilities for LLM reasoning."""
        lines = ["### Available Installed Mods & Capabilities:"]
        for mod in self.installed_mods.values():
            buildings_str = ""
            if mod.new_buildings:
                b_names = [f"`{b.building_id}` ({b.display_name})" for b in mod.new_buildings]
                buildings_str = f" | Buildings: {', '.join(b_names)}"
            lines.append(f"- **{mod.name}** (v{mod.version}): {mod.description}{buildings_str}")
        return "\n".join(lines)

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [m.model_dump() for m in self.installed_mods.values()]
