CREATE TYPE "public"."jetson_workload_status" AS ENUM('idle', 'running', 'overloaded', 'error', 'maintenance');--> statement-breakpoint
CREATE TYPE "public"."network_link_status" AS ENUM('online', 'offline', 'degraded', 'maintenance');--> statement-breakpoint
CREATE TYPE "public"."network_link_type" AS ENUM('point_to_point', 'point_to_multipoint', 'ethernet', 'wifi');--> statement-breakpoint
CREATE TYPE "public"."stream_status" AS ENUM('available', 'unavailable', 'degraded', 'disabled');--> statement-breakpoint
CREATE TABLE "camera_streams" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"camera_id" uuid NOT NULL,
	"name" varchar(120) NOT NULL,
	"status" "stream_status" DEFAULT 'unavailable' NOT NULL,
	"purpose" varchar(50) NOT NULL,
	"protocol" varchar(30) DEFAULT 'rtsp' NOT NULL,
	"stream_url" text,
	"resolution_width" integer,
	"resolution_height" integer,
	"frames_per_second" integer,
	"codec" varchar(30),
	"bitrate_kbps" integer,
	"is_primary" boolean DEFAULT false NOT NULL,
	"last_available_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "jetson_nodes" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"device_id" uuid NOT NULL,
	"hostname" varchar(120) NOT NULL,
	"jetpack_version" varchar(50),
	"cuda_version" varchar(50),
	"tensorrt_version" varchar(50),
	"python_version" varchar(50),
	"workload_status" "jetson_workload_status" DEFAULT 'idle' NOT NULL,
	"maximum_camera_streams" integer DEFAULT 1 NOT NULL,
	"active_camera_streams" integer DEFAULT 0 NOT NULL,
	"ai_service_version" varchar(80),
	"last_model_sync_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "jetson_nodes_device_id_unique" UNIQUE("device_id"),
	CONSTRAINT "jetson_nodes_hostname_unique" UNIQUE("hostname")
);
--> statement-breakpoint
CREATE TABLE "nanostations" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"device_id" uuid NOT NULL,
	"role" varchar(30) NOT NULL,
	"wireless_mode" varchar(50),
	"ssid" varchar(120),
	"frequency_mhz" integer,
	"channel_width_mhz" integer,
	"airmax_enabled" boolean DEFAULT true NOT NULL,
	"management_url" text,
	"antenna_gain_dbi" numeric(5, 2),
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "nanostations_device_id_unique" UNIQUE("device_id")
);
--> statement-breakpoint
CREATE TABLE "network_links" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"link_code" varchar(80) NOT NULL,
	"name" varchar(160) NOT NULL,
	"type" "network_link_type" NOT NULL,
	"status" "network_link_status" DEFAULT 'offline' NOT NULL,
	"source_device_id" uuid NOT NULL,
	"destination_device_id" uuid NOT NULL,
	"distance_meters" integer,
	"frequency_mhz" integer,
	"channel_width_mhz" integer,
	"expected_capacity_mbps" numeric(10, 2),
	"last_checked_at" timestamp with time zone,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "network_links_link_code_unique" UNIQUE("link_code")
);
--> statement-breakpoint
ALTER TABLE "camera_streams" ADD CONSTRAINT "camera_streams_camera_id_cameras_id_fk" FOREIGN KEY ("camera_id") REFERENCES "public"."cameras"("id") ON DELETE cascade ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "jetson_nodes" ADD CONSTRAINT "jetson_nodes_device_id_devices_id_fk" FOREIGN KEY ("device_id") REFERENCES "public"."devices"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "nanostations" ADD CONSTRAINT "nanostations_device_id_devices_id_fk" FOREIGN KEY ("device_id") REFERENCES "public"."devices"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "network_links" ADD CONSTRAINT "network_links_source_device_id_devices_id_fk" FOREIGN KEY ("source_device_id") REFERENCES "public"."devices"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "network_links" ADD CONSTRAINT "network_links_destination_device_id_devices_id_fk" FOREIGN KEY ("destination_device_id") REFERENCES "public"."devices"("id") ON DELETE restrict ON UPDATE cascade;