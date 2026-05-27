from functools import wraps
from typing import Any, Callable


def db_transaction(f: Callable) -> Callable:
    @wraps(f)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        with self._conn:   # auto-commits or rolls back on exception
            cur = self._conn.cursor()
            try:
                return f(self, cur, *args, **kwargs)
            finally:
                cur.close()
    return wrapper
