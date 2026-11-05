from typing import Literal

type PositionOccupancyState = Literal[
    "EMPTY",
    "OCCUPIED",
    "BLOCKED",
    "RETIRED",
]

type LocationState = Literal[
    "UNASSIGNED",
    "PENDING_CONFIRMATION",
    "MISSING",
]
