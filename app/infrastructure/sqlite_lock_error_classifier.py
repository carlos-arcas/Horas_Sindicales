from __future__ import annotations

import sqlite3

from app.application.ports.db_lock_error_classifier import DbLockErrorClassifier


class SQLiteLockErrorClassifier(DbLockErrorClassifier):
    def is_locked_error(self, error: Exception) -> bool:
        return isinstance(error, sqlite3.OperationalError) and "locked" in str(error).lower()
