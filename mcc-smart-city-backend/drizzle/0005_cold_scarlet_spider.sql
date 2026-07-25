CREATE TYPE "public"."event_severity" AS ENUM (
  'info',
  'warning',
  'critical'
);
--> statement-breakpoint

CREATE TYPE "public"."heartbeat_status" AS ENUM (
  'online',
  'offline',
  'degraded',
  'maintenance'
);
--> statement-breakpoint

CREATE TABLE "device_heartbeats" (
                                     "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
                                     "device_id" uuid NOT NULL,
                                     "status" "heartbeat_status" DEFAULT 'online' NOT NULL,
                                     "heartbeat_at" timestamp with time zone DEFAULT now() NOT NULL,
                                     "ip_address" varchar(45),
                                     "firmware_version" varchar(80),
                                     "uptime_seconds" integer,
                                     "metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
                                     "created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint

ALTER TABLE "devices"
DROP CONSTRAINT IF EXISTS "devices_asset_id_asset_id_fk";
--> statement-breakpoint

ALTER TABLE "devices"
DROP CONSTRAINT IF EXISTS "devices_asset_id_assets_id_fk";
--> statement-breakpoint

ALTER TABLE "device_heartbeats"
    ADD CONSTRAINT "device_heartbeats_device_id_devices_id_fk"
        FOREIGN KEY ("device_id")
            REFERENCES "public"."devices"("id")
            ON DELETE cascade
            ON UPDATE cascade;
--> statement-breakpoint

ALTER TABLE "devices"
    ADD CONSTRAINT "devices_asset_id_assets_id_fk"
        FOREIGN KEY ("asset_id")
            REFERENCES "public"."assets"("id")
            ON DELETE restrict
            ON UPDATE cascade;