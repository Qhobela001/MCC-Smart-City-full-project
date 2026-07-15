CREATE TYPE "public"."device_status" AS ENUM('online', 'offline', 'maintenance', 'faulty', 'decommissioned');--> statement-breakpoint
CREATE TYPE "public"."device_type" AS ENUM('camera', 'jetson', 'nanostation', 'server', 'network_switch', 'ups', 'solar_controller', 'other');--> statement-breakpoint
CREATE TABLE "cameras" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"device_id" uuid NOT NULL,
	"camera_code" varchar(80) NOT NULL,
	"rtsp_url" text,
	"stream_path" text,
	"stream_username" varchar(120),
	"is_ai_enabled" boolean DEFAULT true NOT NULL,
	"is_recording_enabled" boolean DEFAULT true NOT NULL,
	"assigned_jetson_id" uuid,
	"field_of_view_description" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "cameras_device_id_unique" UNIQUE("device_id"),
	CONSTRAINT "cameras_camera_code_unique" UNIQUE("camera_code")
);
--> statement-breakpoint
CREATE TABLE "devices" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"device_code" varchar(80) NOT NULL,
	"name" varchar(160) NOT NULL,
	"type" "device_type" NOT NULL,
	"status" "device_status" DEFAULT 'offline' NOT NULL,
	"manufacturer" varchar(120),
	"model" varchar(120),
	"serial_number" varchar(120),
	"ip_address" varchar(45),
	"mac_address" varchar(30),
	"firmware_version" varchar(80),
	"location_id" uuid,
	"installed_at" timestamp with time zone,
	"last_seen_at" timestamp with time zone,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "devices_device_code_unique" UNIQUE("device_code"),
	CONSTRAINT "devices_serial_number_unique" UNIQUE("serial_number")
);
--> statement-breakpoint
CREATE TABLE "locations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(160) NOT NULL,
	"location_code" varchar(50) NOT NULL,
	"address" text,
	"district" varchar(120),
	"latitude" numeric(10, 7),
	"longitude" numeric(10, 7),
	"description" text,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "locations_location_code_unique" UNIQUE("location_code")
);
--> statement-breakpoint
ALTER TABLE "cameras" ADD CONSTRAINT "cameras_device_id_devices_id_fk" FOREIGN KEY ("device_id") REFERENCES "public"."devices"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "cameras" ADD CONSTRAINT "cameras_assigned_jetson_id_devices_id_fk" FOREIGN KEY ("assigned_jetson_id") REFERENCES "public"."devices"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "devices" ADD CONSTRAINT "devices_location_id_locations_id_fk" FOREIGN KEY ("location_id") REFERENCES "public"."locations"("id") ON DELETE set null ON UPDATE cascade;