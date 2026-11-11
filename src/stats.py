# stats.py
# What a search did, so the two solvers can be compared with the same numbers.

from dataclasses import dataclass


@dataclass
class SearchStats:
    """Counters a solver fills in while it runs."""

    expanded: int = 0   # Expansions.  A weighted search can expand one state more than once.
    seen: int = 0       # Distinct states reached.


class SearchLimitReached(Exception):
    """The search expanded as many states as it was allowed to, without an answer."""
