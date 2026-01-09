"""
Environment-based database cursor implementations.

This module provides cursor classes that automatically configure themselves
from environment variables. Useful for applications that need to adapt to
different deployment environments without manual configuration.

Usage:
    from clearskies.cursors.from_environment import MySql, Postgresql, Sqlite

    cursor = MySql()
    cursor.execute("SELECT ...")
"""

from clearskies.cursors.from_environment.mysql import Mysql
from clearskies.cursors.from_environment.postgresql import Postgresql
from clearskies.cursors.from_environment.sqlite import Sqlite

__all__ = ["Mysql", "Postgresql", "Sqlite"]
