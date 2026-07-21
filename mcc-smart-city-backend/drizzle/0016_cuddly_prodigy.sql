CREATE INDEX IF NOT EXISTS "incident_types_severity_idx"
    ON "incident_types" USING btree ("default_severity");