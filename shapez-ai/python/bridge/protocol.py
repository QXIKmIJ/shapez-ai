"""
Data structures and protocol definitions for Shapez AI.
Author: QXIK_mIJ
License: Apache License 2.0
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class EntitySpec(BaseModel):
    building: str
    x: int
    y: int
    rotation: int = 0  # 0, 90, 180, 270
    rotationVariant: int = 0
    originalRotation: Optional[int] = None
    variant: str = "default"
    layer: str = "regular"

    def model_dump(self, *args, **kwargs):
        d = super().model_dump(*args, **kwargs)
        if d.get("originalRotation") is None:
            d["originalRotation"] = d.get("rotation", 0)
        return d

class DeleteCoord(BaseModel):
    x: int
    y: int
    layer: str = "regular"

class GoalInfo(BaseModel):
    shape: str
    required: int
    delivered: float
    throughputOnly: bool = False

class PatchInfo(BaseModel):
    chunkX: int
    chunkY: int
    tileX: int
    tileY: int
    type: str  # "shape" or "color"
    item: str  # e.g. "CuCuCuCu" or "red"
    size: int

class HubInfo(BaseModel):
    bounds: Dict[str, int] = Field(default_factory=lambda: {"x": -2, "y": -2, "w": 4, "h": 4})

class ExistingEntity(BaseModel):
    uid: int
    building: str
    x: int
    y: int
    rotation: int
    rotationVariant: int
    variant: str
    layer: str

class GameState(BaseModel):
    ready: bool
    revision: int
    gameTime: float = 0.0
    level: int = 1
    goal: Optional[GoalInfo] = None
    hub: HubInfo = Field(default_factory=HubInfo)
    unlockedBuildings: List[str] = Field(default_factory=list)
    patches: List[PatchInfo] = Field(default_factory=list)
    entitiesCount: int = 0
    entities: List[ExistingEntity] = Field(default_factory=list)

class RpcRequest(BaseModel):
    type: str = "request"
    id: str
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)

class RpcResponse(BaseModel):
    type: str = "response"
    id: str
    result: Optional[Any] = None
    error: Optional[str] = None

class EventMessage(BaseModel):
    type: str = "event"
    event: str
    data: Dict[str, Any] = Field(default_factory=dict)
