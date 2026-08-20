from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


V380_PROTOCOLS = ("v380", "v380-legacy", "macrovideo")


def ensure_camera_stream_schema(engine: Engine) -> None:
    """
    Upgrade an existing cameras table with dedicated V380 fields.

    SQLAlchemy's create_all() creates missing tables but does not add columns
    to an existing table. This helper follows the same idempotent startup
    upgrade pattern used elsewhere in the MCC backend.

    The compatibility fields are deliberately left untouched during backfill.
    That keeps the currently working gateway operational while the gateway and
    Camera Management UI are migrated to the dedicated fields.
    """

    inspector = inspect(engine)

    if "cameras" not in inspector.get_table_names():
        return

    column_names = {
        column["name"]
        for column in inspector.get_columns("cameras")
    }

    with engine.begin() as connection:
        if "v380_port" not in column_names:
            connection.execute(
                text(
                    "ALTER TABLE cameras "
                    "ADD COLUMN v380_port INTEGER NULL"
                )
            )

        if "v380_device_id" not in column_names:
            connection.execute(
                text(
                    "ALTER TABLE cameras "
                    "ADD COLUMN v380_device_id BIGINT NULL"
                )
            )

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_cameras_v380_device_id "
                "ON cameras (v380_device_id)"
            )
        )

        # Backfill dedicated fields from the temporary compatibility layout.
        # Do not clear rtsp_port/rtsp_path here: the currently deployed gateway
        # still reads them until the next migration stage is installed.
        connection.execute(
            text(
                """
                UPDATE cameras
                SET
                    v380_port = COALESCE(v380_port, rtsp_port),
                    v380_device_id = COALESCE(
                        v380_device_id,
                        CASE
                            WHEN rtsp_path ~ '^[0-9]+$'
                            THEN CAST(rtsp_path AS BIGINT)
                            ELSE NULL
                        END
                    )
                WHERE
                    LOWER(COALESCE(stream_protocol, '')) IN (
                        'v380',
                        'v380-legacy',
                        'macrovideo'
                    )
                """
            )
        )
