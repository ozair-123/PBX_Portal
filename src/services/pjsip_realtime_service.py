"""PJSIP Realtime service for managing endpoints in MariaDB."""

import logging
from typing import List, Dict, Any
from mysql.connector import Error

from ..mariadb_connection import get_mariadb_connection

logger = logging.getLogger(__name__)


class PJSIPRealtimeService:
    """Service for managing PJSIP endpoints in MariaDB realtime database."""

    @staticmethod
    def sync_endpoints(users_with_extensions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sync user extensions to MariaDB PJSIP realtime tables.

        This method:
        1. Connects to MariaDB
        2. Deletes all existing endpoints (clean slate)
        3. Inserts new endpoints for each user
        4. Commits the transaction

        Args:
            users_with_extensions: List of user dicts with extension details

        Returns:
            Dict with sync results:
            {
                "endpoints_synced": int,
                "endpoints_deleted": int
            }

        Raises:
            RuntimeError: If database operation fails
        """
        logger.info(f"Syncing {len(users_with_extensions)} endpoints to MariaDB")

        try:
            with get_mariadb_connection() as conn:
                cursor = conn.cursor()

                # Step 1: Delete all existing portal-managed endpoints
                # We identify our endpoints by the context 'default'
                delete_query = """
                    DELETE e, a, o FROM ps_endpoints e
                    LEFT JOIN ps_auths a ON e.id = a.id
                    LEFT JOIN ps_aors o ON e.id = o.id
                    WHERE e.context = 'default' AND e.id >= '1000' AND e.id <= '1999'
                """
                cursor.execute(delete_query)
                deleted_count = cursor.rowcount
                logger.info(f"Deleted {deleted_count} existing endpoints")

                # Step 2: Insert new endpoints
                synced_count = 0
                for user in users_with_extensions:
                    extension = user.get("extension")
                    if not extension:
                        continue

                    ext_number = str(extension["number"])
                    secret = extension["secret"]
                    name = user["name"]

                    # Insert into ps_endpoints
                    endpoint_query = """
                        INSERT INTO ps_endpoints (id, transport, auth, aors, context, disallow, allow, callerid)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(endpoint_query, (
                        ext_number,
                        'transport-udp-gsm',
                        ext_number,
                        ext_number,
                        'default',
                        'all',
                        'ulaw,alaw',
                        f'"{name}" <{ext_number}>'
                    ))

                    # Insert into ps_auths
                    auth_query = """
                        INSERT INTO ps_auths (id, auth_type, username, password)
                        VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(auth_query, (
                        ext_number,
                        'userpass',
                        ext_number,
                        secret
                    ))

                    # Insert into ps_aors
                    aor_query = """
                        INSERT INTO ps_aors (id, max_contacts, remove_existing)
                        VALUES (%s, %s, %s)
                    """
                    cursor.execute(aor_query, (
                        ext_number,
                        3,
                        'yes'
                    ))

                    synced_count += 1
                    logger.debug(f"Synced endpoint {ext_number} for user {name}")

                # Commit transaction
                conn.commit()
                logger.info(f"Successfully synced {synced_count} endpoints to MariaDB")

                return {
                    "endpoints_synced": synced_count,
                    "endpoints_deleted": deleted_count
                }

        except Error as e:
            logger.error(f"MariaDB error during endpoint sync: {e}")
            raise RuntimeError(f"Failed to sync endpoints to MariaDB: {e}")

        except Exception as e:
            logger.error(f"Unexpected error during endpoint sync: {e}")
            raise RuntimeError(f"Failed to sync endpoints: {e}")
