from sqlalchemy import text
from sqlalchemy.engine import Engine


def ensure_gis_event_links(engine: Engine) -> None:
    """
    Upgrade an existing MCC database so incidents and AI detections
    can reference canonical GIS locations.

    Fresh databases already receive these columns from SQLAlchemy
    metadata. The ALTER statements below are intentionally idempotent
    so existing Docker volumes can be upgraded without deleting data.
    """

    statements = [
        """
        ALTER TABLE ai_detections
        ADD COLUMN IF NOT EXISTS gis_location_id INTEGER
        """,
        """
        ALTER TABLE incidents
        ADD COLUMN IF NOT EXISTS gis_location_id INTEGER
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ai_detections_gis_location_id
        ON ai_detections (gis_location_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_incidents_gis_location_id
        ON incidents (gis_location_id)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_ai_detections_gis_detected_at
        ON ai_detections (gis_location_id, detected_at)
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_attribute a
                  ON a.attrelid = c.conrelid
                 AND a.attnum = ANY(c.conkey)
                WHERE c.contype = 'f'
                  AND c.conrelid = 'ai_detections'::regclass
                  AND a.attname = 'gis_location_id'
            ) THEN
                ALTER TABLE ai_detections
                ADD CONSTRAINT fk_ai_detections_gis_location
                FOREIGN KEY (gis_location_id)
                REFERENCES gis_locations(id)
                ON DELETE SET NULL;
            END IF;
        END
        $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_attribute a
                  ON a.attrelid = c.conrelid
                 AND a.attnum = ANY(c.conkey)
                WHERE c.contype = 'f'
                  AND c.conrelid = 'incidents'::regclass
                  AND a.attname = 'gis_location_id'
            ) THEN
                ALTER TABLE incidents
                ADD CONSTRAINT fk_incidents_gis_location
                FOREIGN KEY (gis_location_id)
                REFERENCES gis_locations(id)
                ON DELETE SET NULL;
            END IF;
        END
        $$;
        """,
        # Conservative backfill: exact location name OR near-identical
        # stored coordinates. This will not guess between multiple matches.
        """
        WITH unique_name_matches AS (
            SELECT
                d.id AS detection_id,
                MIN(l.id) AS location_id
            FROM ai_detections d
            JOIN gis_locations l
              ON d.location_name IS NOT NULL
             AND LOWER(BTRIM(d.location_name)) = LOWER(BTRIM(l.name))
            WHERE d.gis_location_id IS NULL
            GROUP BY d.id
            HAVING COUNT(*) = 1
        )
        UPDATE ai_detections d
        SET gis_location_id = m.location_id
        FROM unique_name_matches m
        WHERE d.id = m.detection_id
          AND d.gis_location_id IS NULL
        """,
        """
        WITH unique_coordinate_matches AS (
            SELECT
                d.id AS detection_id,
                MIN(l.id) AS location_id
            FROM ai_detections d
            JOIN gis_locations l
              ON d.latitude IS NOT NULL
             AND d.longitude IS NOT NULL
             AND ABS(d.latitude - l.latitude) < 0.000001
             AND ABS(d.longitude - l.longitude) < 0.000001
            WHERE d.gis_location_id IS NULL
            GROUP BY d.id
            HAVING COUNT(*) = 1
        )
        UPDATE ai_detections d
        SET gis_location_id = m.location_id
        FROM unique_coordinate_matches m
        WHERE d.id = m.detection_id
          AND d.gis_location_id IS NULL
        """,
        """
        WITH unique_name_matches AS (
            SELECT
                i.id AS incident_id,
                MIN(l.id) AS location_id
            FROM incidents i
            JOIN gis_locations l
              ON i.location_name IS NOT NULL
             AND LOWER(BTRIM(i.location_name)) = LOWER(BTRIM(l.name))
            WHERE i.gis_location_id IS NULL
            GROUP BY i.id
            HAVING COUNT(*) = 1
        )
        UPDATE incidents i
        SET gis_location_id = m.location_id
        FROM unique_name_matches m
        WHERE i.id = m.incident_id
          AND i.gis_location_id IS NULL
        """,
        """
        WITH unique_coordinate_matches AS (
            SELECT
                i.id AS incident_id,
                MIN(l.id) AS location_id
            FROM incidents i
            JOIN gis_locations l
              ON i.latitude IS NOT NULL
             AND i.longitude IS NOT NULL
             AND ABS(i.latitude - l.latitude) < 0.000001
             AND ABS(i.longitude - l.longitude) < 0.000001
            WHERE i.gis_location_id IS NULL
            GROUP BY i.id
            HAVING COUNT(*) = 1
        )
        UPDATE incidents i
        SET gis_location_id = m.location_id
        FROM unique_coordinate_matches m
        WHERE i.id = m.incident_id
          AND i.gis_location_id IS NULL
        """,
        # If an existing linked detection can identify the incident location,
        # backfill the incident conservatively.
        """
        UPDATE incidents i
        SET gis_location_id = d.gis_location_id
        FROM ai_detections d
        WHERE d.incident_id = i.id
          AND d.gis_location_id IS NOT NULL
          AND i.gis_location_id IS NULL
        """,
        # Snapshot hydration for AI detections.
        """
        CREATE OR REPLACE FUNCTION mcc_hydrate_ai_detection_gis_snapshot()
        RETURNS TRIGGER AS $$
        DECLARE
            resolved_name VARCHAR(180);
            resolved_latitude DOUBLE PRECISION;
            resolved_longitude DOUBLE PRECISION;
        BEGIN
            IF NEW.gis_location_id IS NULL THEN
                RETURN NEW;
            END IF;

            IF TG_OP = 'UPDATE' THEN
                IF NEW.gis_location_id IS NOT DISTINCT FROM OLD.gis_location_id THEN
                    RETURN NEW;
                END IF;
            END IF;

            SELECT name, latitude, longitude
                INTO resolved_name, resolved_latitude, resolved_longitude
                FROM gis_locations
                WHERE id = NEW.gis_location_id;

                IF NOT FOUND THEN
                    RAISE EXCEPTION
                        'GIS location % does not exist',
                        NEW.gis_location_id
                        USING ERRCODE = '23503';
                END IF;

            NEW.location_name := resolved_name;
            NEW.latitude := resolved_latitude;
            NEW.longitude := resolved_longitude;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
        """
        DROP TRIGGER IF EXISTS trg_ai_detections_gis_snapshot
        ON ai_detections
        """,
        """
        CREATE TRIGGER trg_ai_detections_gis_snapshot
        BEFORE INSERT OR UPDATE OF gis_location_id
        ON ai_detections
        FOR EACH ROW
        EXECUTE FUNCTION mcc_hydrate_ai_detection_gis_snapshot()
        """,
        # Snapshot hydration for incidents.
        """
        CREATE OR REPLACE FUNCTION mcc_hydrate_incident_gis_snapshot()
        RETURNS TRIGGER AS $$
        DECLARE
            resolved_name VARCHAR(180);
            resolved_latitude DOUBLE PRECISION;
            resolved_longitude DOUBLE PRECISION;
        BEGIN
            IF NEW.gis_location_id IS NULL THEN
                RETURN NEW;
            END IF;

            IF TG_OP = 'UPDATE' THEN
                IF NEW.gis_location_id IS NOT DISTINCT FROM OLD.gis_location_id THEN
                    RETURN NEW;
                END IF;
            END IF;

            SELECT name, latitude, longitude
                INTO resolved_name, resolved_latitude, resolved_longitude
                FROM gis_locations
                WHERE id = NEW.gis_location_id;

                IF NOT FOUND THEN
                    RAISE EXCEPTION
                        'GIS location % does not exist',
                        NEW.gis_location_id
                        USING ERRCODE = '23503';
                END IF;

            NEW.location_name := resolved_name;
            NEW.latitude := resolved_latitude;
            NEW.longitude := resolved_longitude;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
        """
        DROP TRIGGER IF EXISTS trg_incidents_gis_snapshot
        ON incidents
        """,
        """
        CREATE TRIGGER trg_incidents_gis_snapshot
        BEFORE INSERT OR UPDATE OF gis_location_id
        ON incidents
        FOR EACH ROW
        EXECUTE FUNCTION mcc_hydrate_incident_gis_snapshot()
        """,
        # This preserves the already-tested incident engine. Whenever that
        # engine links a detection to an incident, the structured GIS link
        # follows automatically without changing the engine's business logic.
        """
        CREATE OR REPLACE FUNCTION mcc_propagate_detection_gis_to_incident()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.incident_id IS NOT NULL
               AND NEW.gis_location_id IS NOT NULL
            THEN
                UPDATE incidents
                SET gis_location_id = NEW.gis_location_id
                WHERE id = NEW.incident_id
                  AND gis_location_id IS NULL;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """,
        """
        DROP TRIGGER IF EXISTS trg_detection_gis_to_incident
        ON ai_detections
        """,
        """
        CREATE TRIGGER trg_detection_gis_to_incident
        AFTER INSERT OR UPDATE OF incident_id, gis_location_id
        ON ai_detections
        FOR EACH ROW
        EXECUTE FUNCTION mcc_propagate_detection_gis_to_incident()
        """,
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
