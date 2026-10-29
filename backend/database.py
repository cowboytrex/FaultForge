import os
import psycopg
from psycopg.rows import dict_row


def get_services_from_db():
    """Retrieve service records from PostgreSQL."""

    connection = psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5433")),
        dbname=os.getenv("DB_NAME", "faultforge"),
        user=os.getenv("DB_USER", "faultforge"),
        password=os.environ["DB_PASSWORD"],
        connect_timeout=3,
        row_factory=dict_row,
    )

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name, status FROM services ORDER BY id"
                )
                return cursor.fetchall()
    finally:
        connection.close()
