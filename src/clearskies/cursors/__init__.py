"""
This module provides database cursor implementations for various backends.

To use a cursor, import the desired class from this module or from the
from_environment submodule for environment-based configuration.

Usage:
    from clearskies.cursors import Mysql, Postgresql, Sqlite

    cursor = Mysql(database="mydb", ...)
    cursor.execute("SELECT ...")

The from_environment submodule provides cursor classes that automatically
configure themselves from environment variables.

Port forwarding support is available via the port_forwarding submodule.
"""

from clearskies.cursors import from_environment
from clearskies.cursors.cursor import Cursor
from clearskies.cursors.mysql import Mysql
from clearskies.cursors.postgresql import Postgresql
from clearskies.cursors.sqlite import Sqlite

__all__ = ["Cursor", "from_environment", "Mysql", "Postgresql", "Sqlite"]
