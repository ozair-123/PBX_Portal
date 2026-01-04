"""MariaDB connection for Asterisk PJSIP Realtime."""

import logging
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
from typing import Generator

from .config import Config

logger = logging.getLogger(__name__)


@contextmanager
def get_mariadb_connection() -> Generator[mysql.connector.MySQLConnection, None, None]:
    """
    Context manager for MariaDB connections.

    Yields:
        MySQL connection object

    Example:
        with get_mariadb_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ps_endpoints")
            results = cursor.fetchall()
    """
    connection = None
    try:
        connection = mysql.connector.connect(
            host=Config.MARIADB_HOST,
            port=Config.MARIADB_PORT,
            user=Config.MARIADB_USER,
            password=Config.MARIADB_PASSWORD,
            database=Config.MARIADB_DATABASE,
            autocommit=False
        )

        logger.info(f"Connected to MariaDB at {Config.MARIADB_HOST}:{Config.MARIADB_PORT}")
        yield connection

    except Error as e:
        logger.error(f"MariaDB connection error: {e}")
        raise RuntimeError(f"Failed to connect to MariaDB: {e}")

    finally:
        if connection and connection.is_connected():
            connection.close()
            logger.debug("MariaDB connection closed")
