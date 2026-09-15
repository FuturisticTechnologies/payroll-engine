"""Bounds on the paging parameters every list endpoint accepts."""
from __future__ import annotations

from typing import Annotated

from fastapi import Query

MAX_PAGE_SIZE = 500
MAX_OFFSET = 1_000_000

PageLimit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]
PageOffset = Annotated[int, Query(ge=0, le=MAX_OFFSET)]
