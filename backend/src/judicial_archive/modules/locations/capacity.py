from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from judicial_archive.core.errors import InvalidParameterError
from judicial_archive.modules.locations.models import Position, Shelf, Tray

MAX_CAPACITY = 5000


@dataclass(frozen=True)
class CapacityConflict:
    level: str
    code: str
    message: str


@dataclass(frozen=True)
class NewPosition:
    code: str
    label: str


@dataclass(frozen=True)
class TrayAction:
    tray_id: UUID | None
    code: str
    action: Literal["create", "reactivate", "keep", "retire"]
    target_positions: int
    new_positions: tuple[NewPosition, ...]
    reactivate_position_ids: tuple[UUID, ...]
    retire_position_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class CapacityPlan:
    shelf_id: UUID
    target_levels: int
    target_positions_per_level: int
    target_total: int
    current_total: int
    tray_actions: tuple[TrayAction, ...]
    conflicts: tuple[CapacityConflict, ...]

    @property
    def can_apply(self) -> bool:
        return not self.conflicts

    @property
    def trays_to_create(self) -> int:
        return sum(1 for action in self.tray_actions if action.action == "create")

    @property
    def trays_to_reactivate(self) -> int:
        return sum(1 for action in self.tray_actions if action.action == "reactivate")

    @property
    def trays_to_retire(self) -> int:
        return sum(1 for action in self.tray_actions if action.action == "retire")

    @property
    def positions_to_create(self) -> int:
        return sum(len(action.new_positions) for action in self.tray_actions)

    @property
    def positions_to_reactivate(self) -> int:
        return sum(len(action.reactivate_position_ids) for action in self.tray_actions)

    @property
    def positions_to_retire(self) -> int:
        return sum(len(action.retire_position_ids) for action in self.tray_actions)


def _validate_target(levels: int, positions_per_level: int) -> int:
    if levels < 1 or positions_per_level < 1:
        raise InvalidParameterError("La capacidad debe ser positiva.")
    total = levels * positions_per_level
    if total > MAX_CAPACITY:
        raise InvalidParameterError(
            "La capacidad supera el maximo permitido.",
            details={"max_capacity": MAX_CAPACITY, "requested": total},
        )
    return total


def _next_tray_code(used: set[str]) -> str:
    for number in range(1, 10_000):
        candidate = f"N{number:02d}"
        if candidate not in used:
            used.add(candidate)
            return candidate
    raise InvalidParameterError("No fue posible generar un codigo de bandeja.")


def _new_positions(
    tray_code: str,
    used_codes: set[str],
    count: int,
) -> tuple[NewPosition, ...]:
    created: list[NewPosition] = []
    for number in range(1, count + 1):
        candidate = f"P{number:03d}"
        suffix = number
        while candidate in used_codes:
            suffix += 1
            candidate = f"P{suffix:03d}"
        used_codes.add(candidate)
        created.append(
            NewPosition(code=candidate, label=f"Nivel {tray_code} - Posicion {suffix:03d}")
        )
    return tuple(created)


def build_capacity_plan(
    *,
    shelf_id: UUID,
    target_levels: int,
    positions_per_level: int,
    trays: Sequence[Tray],
    positions_by_tray: Mapping[UUID, Sequence[Position]],
    occupied_position_ids: set[UUID],
) -> CapacityPlan:
    target_total = _validate_target(target_levels, positions_per_level)
    ordered = sorted(trays, key=lambda tray: (tray.code, str(tray.id)))
    selected = ordered[:target_levels]
    unselected = ordered[target_levels:]
    used_tray_codes = {tray.code.upper() for tray in ordered}
    actions: list[TrayAction] = []
    conflicts: list[CapacityConflict] = []

    current_total = sum(
        1
        for tray in ordered
        for position in positions_by_tray.get(tray.id, ())
        if position.status != "RETIRED"
    )

    for tray in selected:
        positions = sorted(
            positions_by_tray.get(tray.id, ()),
            key=lambda position: (position.code, str(position.id)),
        )
        non_retired = [position for position in positions if position.status != "RETIRED"]
        retired = [position for position in positions if position.status == "RETIRED"]
        retire_ids: list[UUID] = []
        reactivate_ids: list[UUID] = []
        created: tuple[NewPosition, ...] = ()

        if len(non_retired) > positions_per_level:
            for position in non_retired[positions_per_level:]:
                if position.id in occupied_position_ids:
                    conflicts.append(
                        CapacityConflict(
                            level="position",
                            code=position.code,
                            message="La posicion esta ocupada y quedaria fuera del objetivo.",
                        )
                    )
                elif position.status == "BLOCKED":
                    conflicts.append(
                        CapacityConflict(
                            level="position",
                            code=position.code,
                            message="La posicion esta bloqueada y quedaria fuera del objetivo.",
                        )
                    )
                else:
                    retire_ids.append(position.id)
        elif len(non_retired) < positions_per_level:
            needed = positions_per_level - len(non_retired)
            reactivate_ids = [position.id for position in retired[:needed]]
            remaining = needed - len(reactivate_ids)
            used_codes = {position.code.upper() for position in positions}
            created = _new_positions(tray.code, used_codes, remaining)

        action = "reactivate" if tray.status != "ACTIVE" else "keep"
        actions.append(
            TrayAction(
                tray_id=tray.id,
                code=tray.code,
                action=action,  # type: ignore[arg-type]
                target_positions=positions_per_level,
                new_positions=created,
                reactivate_position_ids=tuple(reactivate_ids),
                retire_position_ids=tuple(retire_ids),
            )
        )

    missing_levels = target_levels - len(selected)
    for _ in range(max(0, missing_levels)):
        code = _next_tray_code(used_tray_codes)
        new_tray_used_codes: set[str] = set()
        created = _new_positions(code, new_tray_used_codes, positions_per_level)
        actions.append(
            TrayAction(
                tray_id=None,
                code=code,
                action="create",
                target_positions=positions_per_level,
                new_positions=created,
                reactivate_position_ids=(),
                retire_position_ids=(),
            )
        )

    for tray in unselected:
        positions = sorted(
            positions_by_tray.get(tray.id, ()),
            key=lambda position: (position.code, str(position.id)),
        )

        unselected_retire_ids: list[UUID] = []

        for position in positions:
            if position.status == "RETIRED":
                continue

            if position.id in occupied_position_ids:
                conflicts.append(
                    CapacityConflict(
                        level="position",
                        code=position.code,
                        message="La posicion esta ocupada; no se puede retirar la bandeja.",
                    )
                )
            elif position.status == "BLOCKED":
                conflicts.append(
                    CapacityConflict(
                        level="position",
                        code=position.code,
                        message="La posicion esta bloqueada; no se puede retirar la bandeja.",
                    )
                )
            else:
                unselected_retire_ids.append(position.id)

        if tray.status == "ACTIVE" or unselected_retire_ids:
            actions.append(
                TrayAction(
                    tray_id=tray.id,
                    code=tray.code,
                    action="retire",
                    target_positions=0,
                    new_positions=(),
                    reactivate_position_ids=(),
                    retire_position_ids=tuple(unselected_retire_ids),
                )
            )

    return CapacityPlan(
        shelf_id=shelf_id,
        target_levels=target_levels,
        target_positions_per_level=positions_per_level,
        target_total=target_total,
        current_total=current_total,
        tray_actions=tuple(actions),
        conflicts=tuple(conflicts),
    )


async def apply_capacity_plan(
    *,
    session: AsyncSession,
    shelf: Shelf,
    plan: CapacityPlan,
    trays_by_id: dict[UUID, Tray],
    positions_by_id: dict[UUID, Position],
) -> None:
    if not plan.can_apply:
        raise InvalidParameterError("El plan de capacidad tiene conflictos.")

    for action in plan.tray_actions:
        if action.action == "create":
            tray = Tray(
                shelf_id=shelf.id,
                code=action.code,
                name=f"Nivel {action.code}",
                position_count=action.target_positions,
                status="ACTIVE",
            )
            session.add(tray)
            await session.flush()
            for new_position in action.new_positions:
                session.add(
                    Position(
                        tray_id=tray.id,
                        code=new_position.code,
                        label=new_position.label,
                        status="AVAILABLE",
                    )
                )
            continue

        tray = trays_by_id[action.tray_id]  # type: ignore
        if action.action == "retire":
            tray.status = "INACTIVE"
        else:
            tray.status = "ACTIVE"
            tray.position_count = action.target_positions

        for position_id in action.reactivate_position_ids:
            positions_by_id[position_id].status = "AVAILABLE"
        for position_id in action.retire_position_ids:
            positions_by_id[position_id].status = "RETIRED"
        for new_position in action.new_positions:
            session.add(
                Position(
                    tray_id=tray.id,
                    code=new_position.code,
                    label=new_position.label,
                    status="AVAILABLE",
                )
            )

    shelf.levels = plan.target_levels
    shelf.positions_per_level = plan.target_positions_per_level
