"""
Deterministic A* grid pathfinder and conveyor router for Shapez AI (N-0.3.3 Smart & Aesthetic Factory).
Features orthogonal turn penalties for clean Manhattan factory layouts, modular processing cells, and line reuse.
Author: QXIK_mIJ
License: Apache License 2.0
"""

import heapq
from typing import Tuple, List, Dict, Set, Optional

try:
    from ..bridge.protocol import EntitySpec
except (ImportError, ValueError):
    from bridge.protocol import EntitySpec

# Cardinal directions and vector offsets
# (dx, dy): rotation in degrees
OFFSETS = {
    (0, -1): 0,    # top
    (1, 0): 90,    # right
    (0, 1): 180,   # bottom
    (-1, 0): 270,  # left
}

ROTATION_TO_DIR = {
    0: (0, -1),
    90: (1, 0),
    180: (0, 1),
    270: (-1, 0),
}

def manhattan_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> int:
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def get_cutter_geometry(cx: int, cy: int, c_rot: int, keep_half: int):
    """
    Returns (footprint_tiles, t_input, in_dir, t_trash, t_out, out_dir):
    - c_rot: 0 (north), 90 (east), 180 (south), 270 (west)
    - keep_half: 0 (left half) or 1 (right half)
    """
    if c_rot == 0:
        footprint = {(cx, cy), (cx + 1, cy)}
        t_input = (cx, cy + 1)
        in_dir = 0
        s0 = (cx, cy - 1)
        s1 = (cx + 1, cy - 1)
        out_dir = 0
    elif c_rot == 90:
        footprint = {(cx, cy), (cx, cy + 1)}
        t_input = (cx - 1, cy)
        in_dir = 90
        s0 = (cx + 1, cy)
        s1 = (cx + 1, cy + 1)
        out_dir = 90
    elif c_rot == 180:
        footprint = {(cx - 1, cy), (cx, cy)}
        t_input = (cx, cy - 1)
        in_dir = 180
        s0 = (cx, cy + 1)
        s1 = (cx - 1, cy + 1)
        out_dir = 180
    else:  # 270
        footprint = {(cx, cy - 1), (cx, cy)}
        t_input = (cx + 1, cy)
        in_dir = 270
        s0 = (cx - 1, cy)
        s1 = (cx - 1, cy - 1)
        out_dir = 270

    t_trash = s0 if keep_half == 1 else s1
    t_out = s1 if keep_half == 1 else s0
    return footprint, t_input, in_dir, t_trash, t_out, out_dir

def get_painter_geometry(px: int, py: int, p_rot: int):
    """
    Returns (footprint_tiles, t_in_shape, shape_in_dir, t_in_color, color_in_dir, t_out, out_dir):
    """
    if p_rot == 0:
        footprint = {(px, py), (px + 1, py)}
        t_in_shape = (px - 1, py)
        shape_in_dir = 90
        t_in_color = (px + 1, py - 1)
        color_in_dir = 180
        t_out = (px + 2, py)
        out_dir = 90
    elif p_rot == 90:
        footprint = {(px, py), (px, py + 1)}
        t_in_shape = (px, py - 1)
        shape_in_dir = 180
        t_in_color = (px + 1, py + 1)
        color_in_dir = 270
        t_out = (px, py + 2)
        out_dir = 180
    elif p_rot == 180:
        footprint = {(px - 1, py), (px, py)}
        t_in_shape = (px + 1, py)
        shape_in_dir = 270
        t_in_color = (px - 1, py + 1)
        color_in_dir = 0
        t_out = (px - 2, py)
        out_dir = 270
    else:  # 270
        footprint = {(px, py - 1), (px, py)}
        t_in_shape = (px, py + 1)
        shape_in_dir = 0
        t_in_color = (px - 1, py - 1)
        color_in_dir = 90
        t_out = (px, py - 2)
        out_dir = 0

    return footprint, t_in_shape, shape_in_dir, t_in_color, color_in_dir, t_out, out_dir

class ConveyorRouter:
    def __init__(self, hub_bounds: Tuple[int, int, int, int] = (-2, -2, 4, 4)):
        # Hub bounds: x, y, w, h -> tiles occupied by Hub
        self.hub_x, self.hub_y, self.hub_w, self.hub_h = hub_bounds
        self.hub_tiles = {
            (self.hub_x + dx, self.hub_y + dy)
            for dx in range(self.hub_w)
            for dy in range(self.hub_h)
        }

    def is_blocked(self, tile: Tuple[int, int], obstacles: Set[Tuple[int, int]]) -> bool:
        return tile in self.hub_tiles or tile in obstacles

    def find_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        obstacles: Set[Tuple[int, int]],
        max_search: int = 5000,
        turn_penalty: float = 1.5
    ) -> Optional[List[Tuple[int, int]]]:
        """
        A* search for a 2D tile path from start to goal.
        Includes turn_penalty to heavily favor straight, clean, aesthetic conveyor runs
        over chaotic zigzagging (Manhattan bus routing).
        """
        if start == goal:
            return [start]

        # state: (f_score, g_cost, current_tile, current_dir)
        open_set = []
        heapq.heappush(open_set, (manhattan_distance(start, goal), 0.0, start, (0, 0)))
        came_from: Dict[Tuple[Tuple[int, int], Tuple[int, int]], Tuple[Tuple[int, int], Tuple[int, int]]] = {}
        cost_so_far: Dict[Tuple[Tuple[int, int], Tuple[int, int]], float] = {(start, (0, 0)): 0.0}
        searched = 0
        final_state = None

        while open_set and searched < max_search:
            searched += 1
            _, current_cost, current, last_dir = heapq.heappop(open_set)

            if current == goal:
                final_state = (current, last_dir)
                break

            for delta in OFFSETS.keys():
                neighbor = (current[0] + delta[0], current[1] + delta[1])
                if neighbor != goal and self.is_blocked(neighbor, obstacles):
                    continue

                is_turn = (last_dir != (0, 0) and last_dir != delta)
                step_cost = 1.0 + (turn_penalty if is_turn else 0.0)
                new_cost = current_cost + step_cost
                next_state = (neighbor, delta)

                if next_state not in cost_so_far or new_cost < cost_so_far[next_state]:
                    cost_so_far[next_state] = new_cost
                    priority = new_cost + manhattan_distance(neighbor, goal)
                    heapq.heappush(open_set, (priority, new_cost, neighbor, delta))
                    came_from[next_state] = (current, last_dir)

        if not final_state:
            return None

        # Reconstruct path
        path = []
        curr_state = final_state
        visited = set()
        while curr_state in came_from and curr_state not in visited:
            visited.add(curr_state)
            path.append(curr_state[0])
            curr_state = came_from[curr_state]
        path.append(start)
        path.reverse()
        return path

    def path_to_belts(
        self,
        path: List[Tuple[int, int]],
        start_direction: Optional[int] = None,
        final_rotation: Optional[int] = None
    ) -> List[EntitySpec]:
        """Converts an ordered list of tiles into Belt EntitySpecs with correct rotations and rotationVariants."""
        if not path:
            return []

        specs = []
        for i in range(len(path)):
            curr = path[i]

            # Inbound movement vector into curr
            if i == 0:
                if start_direction is not None and start_direction in ROTATION_TO_DIR:
                    d_in = ROTATION_TO_DIR[start_direction]
                elif len(path) > 1:
                    d_in = (path[1][0] - curr[0], path[1][1] - curr[1])
                else:
                    d_in = (0, -1)
            else:
                d_in = (curr[0] - path[i - 1][0], curr[1] - path[i - 1][1])

            # Outbound movement vector out of curr
            if i < len(path) - 1:
                d_out = (path[i + 1][0] - curr[0], path[i + 1][1] - curr[1])
            else:
                if final_rotation is not None and final_rotation in ROTATION_TO_DIR:
                    d_out = ROTATION_TO_DIR[final_rotation]
                else:
                    d_out = d_in

            in_rot = OFFSETS.get(d_in, 0)
            out_rot = OFFSETS.get(d_out, in_rot)

            rot = in_rot
            rot_diff = (out_rot - in_rot) % 360

            if rot_diff == 270:
                # Left turn
                variant = 1
            elif rot_diff == 90:
                # Right turn
                variant = 2
            else:
                # Straight
                variant = 0

            specs.append(EntitySpec(
                building="belt",
                x=curr[0],
                y=curr[1],
                rotation=rot,
                rotationVariant=variant
            ))

        return specs

    def find_nearest_hub_slot(
        self,
        from_pos: Tuple[int, int],
        obstacles: Optional[Set[Tuple[int, int]]] = None
    ) -> Tuple[Tuple[int, int], int]:
        """
        Returns the optimal ((entry_x, entry_y), belt_rotation_into_hub)
        for any source position.
        Hub occupies [-2..1, -2..1].
        """
        slots = []
        # Top side (y = -3, moving south/bottom into y = -2)
        for x in range(-2, 2):
            slots.append(((x, -3), 180))
        # Bottom side (y = 2, moving north/top into y = 1)
        for x in range(-2, 2):
            slots.append(((x, 2), 0))
        # Left side (x = -3, moving east/right into x = -2)
        for y in range(-2, 2):
            slots.append(((-3, y), 90))
        # Right side (x = 2, moving west/left into x = 1)
        for y in range(-2, 2):
            slots.append(((2, y), 270))

        if obstacles:
            free_slots = [s for s in slots if s[0] not in obstacles]
            if free_slots:
                slots = free_slots

        best_slot = min(slots, key=lambda s: manhattan_distance(from_pos, s[0]))
        return best_slot

    def plan_miner_and_conveyor(
        self,
        patch_tile: Tuple[int, int],
        hub_entry_tile: Tuple[int, int],
        entry_direction: int,
        obstacles: Set[Tuple[int, int]]
    ) -> Optional[List[EntitySpec]]:
        """
        Plans a miner on the patch and an aesthetic conveyor belt directly connecting into the Hub.
        """
        miner_x, miner_y = int(round(patch_tile[0])), int(round(patch_tile[1]))

        # Find best exit direction from the miner towards the hub entry
        best_delta = None
        min_dist = float("inf")
        for delta in OFFSETS.keys():
            neighbor = (miner_x + delta[0], miner_y + delta[1])
            if not self.is_blocked(neighbor, obstacles):
                d = manhattan_distance(neighbor, hub_entry_tile)
                if d < min_dist:
                    min_dist = d
                    best_delta = delta

        if not best_delta:
            return None

        miner_rot = OFFSETS[best_delta]
        miner_spec = EntitySpec(
            building="miner",
            x=miner_x,
            y=miner_y,
            rotation=miner_rot,
            variant="default"
        )

        belt_start = (miner_x + best_delta[0], miner_y + best_delta[1])
        obs = obstacles | {(miner_x, miner_y)}

        path = self.find_path(belt_start, hub_entry_tile, obs)
        if not path:
            return None

        belt_specs = self.path_to_belts(path, start_direction=miner_rot, final_rotation=entry_direction)
        return [miner_spec] + belt_specs

    def plan_cutter_and_conveyor(
        self,
        patch_tile: Tuple[int, int],
        hub_entry_tile: Tuple[int, int],
        entry_direction: int,
        obstacles: Set[Tuple[int, int]],
        keep_half: int = 0,
        rotation: int = 0
    ) -> Optional[List[EntitySpec]]:
        """
        Plans a compact, symmetrical processing block:
        Miner -> Inbound Belt -> Cutter (2x1) -> Trash on unwanted output -> (Optional Rotater) -> Outbound Belt -> Hub.
        """
        miner_x, miner_y = int(round(patch_tile[0])), int(round(patch_tile[1]))

        best_delta = None
        min_dist = float("inf")
        for delta in OFFSETS.keys():
            neighbor = (miner_x + delta[0], miner_y + delta[1])
            if not self.is_blocked(neighbor, obstacles):
                d = manhattan_distance(neighbor, hub_entry_tile)
                if d < min_dist:
                    min_dist = d
                    best_delta = delta

        if not best_delta:
            return None

        miner_rot = OFFSETS[best_delta]
        miner_spec = EntitySpec(
            building="miner",
            x=miner_x,
            y=miner_y,
            rotation=miner_rot,
            variant="default"
        )

        belt_start = (miner_x + best_delta[0], miner_y + best_delta[1])
        base_obs = obstacles | {(miner_x, miner_y)}

        best_plan = None
        min_total_cost = float("inf")

        # Determine rotater variant if rotation is needed
        rot_variant = None
        if rotation == 90:
            rot_variant = "default"  # CW
        elif rotation == 180:
            rot_variant = "rotate180"
        elif rotation == 270:
            rot_variant = "ccw"

        # Preferred cutter orientations sorted by alignment with general vector to Hub
        dx_to_hub = hub_entry_tile[0] - miner_x
        dy_to_hub = hub_entry_tile[1] - miner_y
        orientations = [0, 90, 180, 270]
        if abs(dx_to_hub) > abs(dy_to_hub):
            target_rot = 90 if dx_to_hub > 0 else 270
        else:
            target_rot = 180 if dy_to_hub > 0 else 0
        orientations.sort(key=lambda r: 0 if r == target_rot else (1 if abs(r - target_rot) == 90 else 2))

        # Scan a local grid around the patch for a compact, neat cutter installation
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                cx = miner_x + dx
                cy = miner_y + dy

                for c_rot in orientations:
                    footprint, t_input, in_dir, t_trash, t_raw_out, out_dir = get_cutter_geometry(cx, cy, c_rot, keep_half)
                    needed = footprint | {t_input, t_trash, t_raw_out}

                    if rot_variant:
                        dx_o, dy_o = ROTATION_TO_DIR[out_dir]
                        t_rotater = t_raw_out
                        t_out = (t_rotater[0] + dx_o, t_rotater[1] + dy_o)
                        needed |= {t_rotater, t_out}
                    else:
                        t_rotater = None
                        t_out = t_raw_out

                    if any(self.is_blocked(t, base_obs) for t in needed):
                        continue

                    cutter_occupied = footprint | {t_trash}
                    if t_rotater:
                        cutter_occupied.add(t_rotater)

                    # Path 1: miner -> cutter input
                    obs1 = base_obs | cutter_occupied | {t_out}
                    path1 = self.find_path(belt_start, t_input, obs1, max_search=1200)
                    if not path1:
                        continue

                    # Path 2: processing output -> hub
                    obs2 = base_obs | set(path1) | cutter_occupied
                    path2 = self.find_path(t_out, hub_entry_tile, obs2, max_search=2500)
                    if not path2:
                        continue

                    # Cost metric balances compact closeness to miner and straight lines
                    cost = len(path1) * 1.5 + len(path2)
                    if cost < min_total_cost:
                        min_total_cost = cost
                        best_plan = (cx, cy, c_rot, t_trash, t_rotater, out_dir, in_dir, path1, path2)

        if not best_plan:
            return None

        cx, cy, c_rot, t_trash, t_rotater, out_dir, in_dir, path1, path2 = best_plan

        path1_belts = self.path_to_belts(path1, start_direction=miner_rot, final_rotation=in_dir)

        cutter_spec = EntitySpec(
            building="cutter",
            x=cx,
            y=cy,
            rotation=c_rot,
            variant="default"
        )

        trash_spec = EntitySpec(
            building="trash",
            x=t_trash[0],
            y=t_trash[1],
            rotation=out_dir,
            variant="default"
        )

        mid_machines = [cutter_spec, trash_spec]
        if t_rotater and rot_variant:
            mid_machines.append(EntitySpec(
                building="rotater",
                x=t_rotater[0],
                y=t_rotater[1],
                rotation=out_dir,
                variant=rot_variant
            ))

        path2_belts = self.path_to_belts(path2, start_direction=out_dir, final_rotation=entry_direction)
        return [miner_spec] + path1_belts + mid_machines + path2_belts

    def plan_painting_line(
        self,
        shape_patch_tile: Tuple[int, int],
        color_patch_tile: Tuple[int, int],
        hub_entry_tile: Tuple[int, int],
        entry_direction: int,
        obstacles: Set[Tuple[int, int]]
    ) -> Optional[List[EntitySpec]]:
        """
        Plans a compact, aesthetic painting production line:
        - Shape Miner -> Conveyor into Painter shape input at (px, py) from left (rot 90).
        - Color Miner -> Conveyor into Painter color input at (px+1, py) from top (rot 180).
        - Painter (2x1 at (px, py), rotation 0).
        - Outbound Conveyor from (px+2, py) with rotation 90 -> Hub entry slot.
        """
        sm_x, sm_y = int(round(shape_patch_tile[0])), int(round(shape_patch_tile[1]))
        cm_x, cm_y = int(round(color_patch_tile[0])), int(round(color_patch_tile[1]))

        # 1. Best delta for shape miner
        best_sm_delta = None
        min_sm_dist = float("inf")
        for delta in OFFSETS.keys():
            n = (sm_x + delta[0], sm_y + delta[1])
            if not self.is_blocked(n, obstacles):
                d = manhattan_distance(n, hub_entry_tile)
                if d < min_sm_dist:
                    min_sm_dist = d
                    best_sm_delta = delta

        # 2. Best delta for color miner
        best_cm_delta = None
        min_cm_dist = float("inf")
        for delta in OFFSETS.keys():
            n = (cm_x + delta[0], cm_y + delta[1])
            if not self.is_blocked(n, obstacles):
                d = manhattan_distance(n, hub_entry_tile)
                if d < min_cm_dist:
                    min_cm_dist = d
                    best_cm_delta = delta

        if not best_sm_delta or not best_cm_delta:
            return None

        sm_rot = OFFSETS[best_sm_delta]
        cm_rot = OFFSETS[best_cm_delta]

        shape_belt_start = (sm_x + best_sm_delta[0], sm_y + best_sm_delta[1])
        color_belt_start = (cm_x + best_cm_delta[0], cm_y + best_cm_delta[1])

        base_obs = obstacles | {(sm_x, sm_y), (cm_x, cm_y)}

        best_plan = None
        min_total_cost = float("inf")

        # Scan candidate locations for painter placement near Hub entry tile
        hx, hy = hub_entry_tile
        for py in range(hy - 6, hy + 7):
            for px in range(hx - 6, hx + 7):
                for p_rot in [0, 90, 180, 270]:
                    footprint, t_in_shape, shape_in_dir, t_in_color, color_in_dir, t_out, out_dir = get_painter_geometry(px, py, p_rot)
                    needed = footprint | {t_in_shape, t_in_color, t_out}
                    if any(self.is_blocked(t, base_obs) for t in needed):
                        continue

                    # Path 1 (Fast Prune): Painter output -> Hub entry
                    obs_out = base_obs | footprint | {t_in_shape, t_in_color}
                    path_out = self.find_path(t_out, hub_entry_tile, obs_out, max_search=400)
                    if not path_out:
                        continue

                    # Path 2: shape miner -> painter shape input
                    obs1 = base_obs | footprint | {t_in_color, t_out, hub_entry_tile} | set(path_out)
                    path_shape = self.find_path(shape_belt_start, t_in_shape, obs1, max_search=2000)
                    if not path_shape:
                        continue

                    # Path 3: color miner -> painter color input
                    obs2 = base_obs | footprint | {t_in_shape, t_out, hub_entry_tile} | set(path_shape) | set(path_out)
                    path_color = self.find_path(color_belt_start, t_in_color, obs2, max_search=2000)
                    if not path_color:
                        continue

                    cost = len(path_shape) + len(path_color) + len(path_out)
                    if cost < min_total_cost:
                        min_total_cost = cost
                        best_plan = (px, py, p_rot, shape_in_dir, color_in_dir, out_dir, path_shape, path_color, path_out)

        if not best_plan:
            return None

        px, py, p_rot, shape_in_dir, color_in_dir, out_dir, path_shape, path_color, path_out = best_plan

        shape_miner = EntitySpec(building="miner", x=sm_x, y=sm_y, rotation=sm_rot, variant="default")
        color_miner = EntitySpec(building="miner", x=cm_x, y=cm_y, rotation=cm_rot, variant="default")
        painter = EntitySpec(building="painter", x=px, y=py, rotation=p_rot, variant="default")

        belts_shape = self.path_to_belts(path_shape, start_direction=sm_rot, final_rotation=shape_in_dir)
        belts_color = self.path_to_belts(path_color, start_direction=cm_rot, final_rotation=color_in_dir)
        belts_out = self.path_to_belts(path_out, start_direction=out_dir, final_rotation=entry_direction)

        return [shape_miner, color_miner, painter] + belts_shape + belts_color + belts_out

    def plan_cut_and_paint_line(
        self,
        shape_patch_tile: Tuple[int, int],
        color_patch_tile: Tuple[int, int],
        hub_entry_tile: Tuple[int, int],
        entry_direction: int,
        obstacles: Set[Tuple[int, int]],
        keep_half: int = 1,
        rotation: int = 0
    ) -> Optional[List[EntitySpec]]:
        """
        Plans a compact, aesthetic cut & paint production line with 4-way machine orientation:
        - Raw Shape Miner -> Inbound Conveyor -> Cutter (2x1, any 4 orientations) -> Trash on unwanted half.
        - Kept half output -> Optional inline Rotater (if rotation != 0) -> Conveyor into Painter shape input.
        - Color Miner -> Conveyor into Painter color input (Painter 2x1, any 4 orientations).
        - Painter output -> Conveyor -> Hub entry slot.
        """
        sm_x, sm_y = int(round(shape_patch_tile[0])), int(round(shape_patch_tile[1]))
        cm_x, cm_y = int(round(color_patch_tile[0])), int(round(color_patch_tile[1]))

        # 1. Best delta for shape miner
        best_sm_delta = None
        min_sm_dist = float("inf")
        for delta in OFFSETS.keys():
            n = (sm_x + delta[0], sm_y + delta[1])
            if not self.is_blocked(n, obstacles):
                d = manhattan_distance(n, hub_entry_tile)
                if d < min_sm_dist:
                    min_sm_dist = d
                    best_sm_delta = delta

        # 2. Best delta for color miner
        best_cm_delta = None
        min_cm_dist = float("inf")
        for delta in OFFSETS.keys():
            n = (cm_x + delta[0], cm_y + delta[1])
            if not self.is_blocked(n, obstacles):
                d = manhattan_distance(n, hub_entry_tile)
                if d < min_cm_dist:
                    min_cm_dist = d
                    best_cm_delta = delta

        if not best_sm_delta or not best_cm_delta:
            return None

        sm_rot = OFFSETS[best_sm_delta]
        cm_rot = OFFSETS[best_cm_delta]

        shape_belt_start = (sm_x + best_sm_delta[0], sm_y + best_sm_delta[1])
        color_belt_start = (cm_x + best_cm_delta[0], cm_y + best_cm_delta[1])

        base_obs = obstacles | {(sm_x, sm_y), (cm_x, cm_y)}

        rot_variant = None
        if rotation == 90:
            rot_variant = "default"
        elif rotation == 180:
            rot_variant = "rotate180"
        elif rotation == 270:
            rot_variant = "ccw"

        # 3. Search best Cutter placements across all 4 orientations
        dx_to_hub = hub_entry_tile[0] - sm_x
        dy_to_hub = hub_entry_tile[1] - sm_y
        c_orientations = [0, 90, 180, 270]
        if abs(dx_to_hub) > abs(dy_to_hub):
            target_c_rot = 90 if dx_to_hub > 0 else 270
        else:
            target_c_rot = 180 if dy_to_hub > 0 else 0
        c_orientations.sort(key=lambda r: 0 if r == target_c_rot else (1 if abs(r - target_c_rot) == 90 else 2))

        cutter_candidates = []
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                cx = sm_x + dx
                cy = sm_y + dy
                for c_rot in c_orientations:
                    footprint, t_input, in_dir, t_trash, t_raw_out, c_out_dir = get_cutter_geometry(cx, cy, c_rot, keep_half)
                    needed = footprint | {t_input, t_trash, t_raw_out}
                    if rot_variant:
                        dx_o, dy_o = ROTATION_TO_DIR[c_out_dir]
                        t_rotater = t_raw_out
                        t_cutter_out = (t_rotater[0] + dx_o, t_rotater[1] + dy_o)
                        needed |= {t_rotater, t_cutter_out}
                    else:
                        t_rotater = None
                        t_cutter_out = t_raw_out

                    if any(self.is_blocked(t, base_obs) for t in needed):
                        continue

                    cutter_occupied = footprint | {t_trash}
                    if t_rotater:
                        cutter_occupied.add(t_rotater)

                    obs_c = base_obs | cutter_occupied | {t_cutter_out}
                    p_in = self.find_path(shape_belt_start, t_input, obs_c, max_search=800)
                    if not p_in:
                        continue

                    cost = len(p_in) * 1.5 + manhattan_distance(t_cutter_out, hub_entry_tile)
                    cutter_candidates.append((cost, cx, cy, c_rot, t_trash, t_rotater, t_cutter_out, c_out_dir, in_dir, p_in, cutter_occupied))

        if not cutter_candidates:
            return None

        cutter_candidates.sort(key=lambda c: c[0])
        best_overall_plan = None
        min_total_cost = float("inf")

        hx, hy = hub_entry_tile
        for _, cx, cy, c_rot, t_trash, t_rotater, t_cutter_out, c_out_dir, in_dir, path_sm_to_cutter, cutter_occupied in cutter_candidates[:2]:
            cutter_obs = base_obs | set(path_sm_to_cutter) | cutter_occupied

            # 4. Search candidate locations for Painter placement near Hub entry tile
            for py in range(hy - 6, hy + 7):
                for px in range(hx - 6, hx + 7):
                    for p_rot in [0, 90, 180, 270]:
                        p_footprint, t_in_shape, shape_in_dir, t_in_color, color_in_dir, t_out, p_out_dir = get_painter_geometry(px, py, p_rot)
                        needed = p_footprint | {t_in_shape, t_in_color, t_out}
                        if any(self.is_blocked(t, cutter_obs) for t in needed):
                            continue

                        # Path 1 (Fast Prune): Painter output to Hub entry slot
                        obs_out = cutter_obs | p_footprint | {t_in_shape, t_in_color}
                        path_out = self.find_path(t_out, hub_entry_tile, obs_out, max_search=400)
                        if not path_out:
                            continue

                        # Path 2: Cutter output (facing c_out_dir) to Painter shape input
                        obs1 = cutter_obs | p_footprint | {t_in_color, t_out, hub_entry_tile} | set(path_out)
                        path_shape = self.find_path(t_cutter_out, t_in_shape, obs1, max_search=2000)
                        if not path_shape:
                            continue

                        # Path 3: Color miner to Painter color input
                        obs2 = cutter_obs | p_footprint | {t_in_shape, t_out, hub_entry_tile} | set(path_shape) | set(path_out)
                        path_color = self.find_path(color_belt_start, t_in_color, obs2, max_search=2000)
                        if not path_color:
                            continue

                        total_cost = len(path_sm_to_cutter) + len(path_shape) + len(path_color) + len(path_out)
                        if total_cost < min_total_cost:
                            min_total_cost = total_cost
                            best_overall_plan = (
                                cx, cy, c_rot, t_trash, t_rotater, c_out_dir, in_dir, path_sm_to_cutter,
                                px, py, p_rot, shape_in_dir, color_in_dir, p_out_dir,
                                path_shape, path_color, path_out
                            )

            if best_overall_plan:
                break

        if not best_overall_plan:
            return None

        (
            cx, cy, c_rot, t_trash, t_rotater, c_out_dir, in_dir, path_sm_to_cutter,
            px, py, p_rot, shape_in_dir, color_in_dir, p_out_dir,
            path_shape, path_color, path_out
        ) = best_overall_plan

        shape_miner = EntitySpec(building="miner", x=sm_x, y=sm_y, rotation=sm_rot, variant="default")
        color_miner = EntitySpec(building="miner", x=cm_x, y=cm_y, rotation=cm_rot, variant="default")
        cutter_spec = EntitySpec(building="cutter", x=cx, y=cy, rotation=c_rot, variant="default")
        trash_spec = EntitySpec(building="trash", x=t_trash[0], y=t_trash[1], rotation=c_out_dir, variant="default")
        painter_spec = EntitySpec(building="painter", x=px, y=py, rotation=p_rot, variant="default")

        mid_machines = [cutter_spec, trash_spec]
        if t_rotater and rot_variant:
            mid_machines.append(EntitySpec(
                building="rotater",
                x=t_rotater[0],
                y=t_rotater[1],
                rotation=c_out_dir,
                variant=rot_variant
            ))

        belts_sm_to_cutter = self.path_to_belts(path_sm_to_cutter, start_direction=sm_rot, final_rotation=in_dir)
        belts_shape = self.path_to_belts(path_shape, start_direction=c_out_dir, final_rotation=shape_in_dir)
        belts_color = self.path_to_belts(path_color, start_direction=cm_rot, final_rotation=color_in_dir)
        belts_out = self.path_to_belts(path_out, start_direction=p_out_dir, final_rotation=entry_direction)

        return (
            [shape_miner] + belts_sm_to_cutter + mid_machines +
            [color_miner, painter_spec] + belts_shape + belts_color + belts_out
        )


    def plan_mix_and_paint_line(
        self,
        shape_patch_tile: Tuple[int, int],
        color1_patch_tile: Tuple[int, int],
        color2_patch_tile: Tuple[int, int],
        hub_entry_tile: Tuple[int, int],
        entry_direction: int,
        obstacles: Set[Tuple[int, int]]
    ) -> Optional[List[EntitySpec]]:
        """
        Plans a compact, modular multi-stage production line:
        - Shape Miner on shape_patch_tile (e.g. CuCuCuCu).
        - Color 1 Miner on color1_patch_tile (e.g. Red).
        - Color 2 Miner on color2_patch_tile (e.g. Blue).
        - Color Mixer (2x1 at (px+1, py-2), rotation 180) mixing Color 1 + Color 2 into composite dye (e.g. Purple).
        - Direct vertical feeder belt at (px+1, py-1) with rotation 180 (South) into Painter.
        - Painter (2x1 at (px, py), rotation 0) receiving shape from left (East 90) and mixed dye from top (South 180).
        - Outbound conveyor from (px+2, py) with rotation 90 (East) directly into Hub entry slot.
        """
        sm_x, sm_y = int(round(shape_patch_tile[0])), int(round(shape_patch_tile[1]))
        c1_x, c1_y = int(round(color1_patch_tile[0])), int(round(color1_patch_tile[1]))
        c2_x, c2_y = int(round(color2_patch_tile[0])), int(round(color2_patch_tile[1]))

        # 1. Best delta for shape miner
        best_sm_delta = None
        min_sm_dist = float("inf")
        for delta in OFFSETS.keys():
            n = (sm_x + delta[0], sm_y + delta[1])
            if not self.is_blocked(n, obstacles):
                d = manhattan_distance(n, hub_entry_tile)
                if d < min_sm_dist:
                    min_sm_dist = d
                    best_sm_delta = delta

        # 2. Best delta for color 1 miner
        best_c1_delta = None
        min_c1_dist = float("inf")
        for delta in OFFSETS.keys():
            n = (c1_x + delta[0], c1_y + delta[1])
            if not self.is_blocked(n, obstacles):
                d = manhattan_distance(n, hub_entry_tile)
                if d < min_c1_dist:
                    min_c1_dist = d
                    best_c1_delta = delta

        # 3. Best delta for color 2 miner
        best_c2_delta = None
        min_c2_dist = float("inf")
        for delta in OFFSETS.keys():
            n = (c2_x + delta[0], c2_y + delta[1])
            if not self.is_blocked(n, obstacles):
                d = manhattan_distance(n, hub_entry_tile)
                if d < min_c2_dist:
                    min_c2_dist = d
                    best_c2_delta = delta

        if not best_sm_delta or not best_c1_delta or not best_c2_delta:
            return None

        sm_rot = OFFSETS[best_sm_delta]
        c1_rot = OFFSETS[best_c1_delta]
        c2_rot = OFFSETS[best_c2_delta]

        shape_belt_start = (sm_x + best_sm_delta[0], sm_y + best_sm_delta[1])
        c1_belt_start = (c1_x + best_c1_delta[0], c1_y + best_c1_delta[1])
        c2_belt_start = (c2_x + best_c2_delta[0], c2_y + best_c2_delta[1])

        base_obs = obstacles | {(sm_x, sm_y), (c1_x, c1_y), (c2_x, c2_y)}

        best_plan = None
        min_total_cost = float("inf")

        center_x = (sm_x + c1_x + hub_entry_tile[0]) // 3
        center_y = (sm_y + c1_y + hub_entry_tile[1]) // 3

        # Prioritize candidate cells near the Hub entry slot for clean, compact delivery runs
        search_candidates = []
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                search_candidates.append((hub_entry_tile[0] + dx, hub_entry_tile[1] + dy))
        # Fallback to geometric center
        for dy in range(-8, 9):
            for dx in range(-8, 9):
                cand = (center_x + dx, center_y + dy)
                if cand not in search_candidates:
                    search_candidates.append(cand)

        for px, py in search_candidates:
            t_p1 = (px, py)
            t_p2 = (px + 1, py)
            t_m1 = (px, py - 2)
            t_m2 = (px + 1, py - 2)
            t_mid_belt = (px + 1, py - 1)
            t_in_c1 = (px + 1, py - 3)
            t_in_c2 = (px, py - 3)
            t_in_shape = (px - 1, py)
            t_out = (px + 2, py)

            cell_footprint = {t_p1, t_p2, t_m1, t_m2, t_mid_belt, t_in_c1, t_in_c2, t_in_shape, t_out}
            if any(self.is_blocked(t, base_obs) for t in cell_footprint):
                continue

            # Path 1: Output from (px+2, py) to hub_entry_tile
            obs_out = base_obs | cell_footprint
            obs_out.discard(t_out)
            path_out = self.find_path(t_out, hub_entry_tile, obs_out, max_search=3000)
            if not path_out:
                continue

            # Path 2: Shape from shape_belt_start to t_in_shape
            obs_shape = base_obs | cell_footprint | set(path_out)
            obs_shape.discard(t_in_shape)
            path_shape = self.find_path(shape_belt_start, t_in_shape, obs_shape, max_search=4000)
            if not path_shape:
                continue

            # Path 3: Color 1 from c1_belt_start to t_in_c1
            obs_c1 = base_obs | cell_footprint | set(path_out) | set(path_shape)
            obs_c1.discard(t_in_c1)
            path_c1 = self.find_path(c1_belt_start, t_in_c1, obs_c1, max_search=4000)
            if not path_c1:
                continue

            # Path 4: Color 2 from c2_belt_start to t_in_c2
            obs_c2 = base_obs | cell_footprint | set(path_out) | set(path_shape) | set(path_c1)
            obs_c2.discard(t_in_c2)
            path_c2 = self.find_path(c2_belt_start, t_in_c2, obs_c2, max_search=5000)
            if not path_c2:
                continue

            cost = len(path_out) + len(path_shape) + len(path_c1) + len(path_c2)
            if cost < min_total_cost:
                min_total_cost = cost
                best_plan = (px, py, path_out, path_shape, path_c1, path_c2)
                break

        if not best_plan:
            return None

        px, py, path_out, path_shape, path_c1, path_c2 = best_plan
        specs = []

        # Miners
        specs.append(EntitySpec(building="miner", x=sm_x, y=sm_y, rotation=sm_rot, variant="default"))
        specs.append(EntitySpec(building="miner", x=c1_x, y=c1_y, rotation=c1_rot, variant="default"))
        specs.append(EntitySpec(building="miner", x=c2_x, y=c2_y, rotation=c2_rot, variant="default"))

        # Input belt paths
        specs.extend(self.path_to_belts(path_shape, start_direction=sm_rot, final_rotation=90))
        specs.extend(self.path_to_belts(path_c1, start_direction=c1_rot, final_rotation=180))
        specs.extend(self.path_to_belts(path_c2, start_direction=c2_rot, final_rotation=180))

        # Mixer at (px+1, py-2) with rotation 180 (occupies (px, py-2) and (px+1, py-2))
        specs.append(EntitySpec(building="mixer", x=px + 1, y=py - 2, rotation=180, variant="default"))

        # Interconnecting belt from mixer ejector to painter
        specs.append(EntitySpec(building="belt", x=px + 1, y=py - 1, rotation=180, variant="default"))

        # Painter at (px, py) with rotation 0
        specs.append(EntitySpec(building="painter", x=px, y=py, rotation=0, variant="default"))

        # Outbound path to hub
        specs.extend(self.path_to_belts(path_out, start_direction=90, final_rotation=entry_direction))

        return specs

