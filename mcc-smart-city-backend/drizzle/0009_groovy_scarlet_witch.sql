CREATE TYPE "public"."power_system_status" AS ENUM('planned', 'online', 'degraded', 'offline', 'maintenance');--> statement-breakpoint
CREATE TYPE "public"."power_system_type" AS ENUM('solar_battery', 'mains_ups', 'hybrid', 'other');--> statement-breakpoint
CREATE TABLE "power_systems" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"power_system_code" varchar(80) NOT NULL,
	"name" varchar(160) NOT NULL,
	"type" "power_system_type" NOT NULL,
	"status" "power_system_status" DEFAULT 'planned' NOT NULL,
	"location_id" uuid NOT NULL,
	"solar_panel_asset_id" uuid,
	"battery_asset_id" uuid,
	"charge_controller_asset_id" uuid,
	"ups_asset_id" uuid,
	"nominal_system_voltage" numeric(6, 2),
	"solar_capacity_watts" numeric(10, 2),
	"battery_capacity_amp_hours" numeric(10, 2),
	"maximum_load_watts" numeric(10, 2),
	"low_battery_threshold_percent" numeric(5, 2) DEFAULT '20' NOT NULL,
	"last_checked_at" timestamp with time zone,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "power_systems_power_system_code_unique" UNIQUE("power_system_code")
);
--> statement-breakpoint
ALTER TABLE "power_systems" ADD CONSTRAINT "power_systems_location_id_locations_id_fk" FOREIGN KEY ("location_id") REFERENCES "public"."locations"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "power_systems" ADD CONSTRAINT "power_systems_solar_panel_asset_id_assets_id_fk" FOREIGN KEY ("solar_panel_asset_id") REFERENCES "public"."assets"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "power_systems" ADD CONSTRAINT "power_systems_battery_asset_id_assets_id_fk" FOREIGN KEY ("battery_asset_id") REFERENCES "public"."assets"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "power_systems" ADD CONSTRAINT "power_systems_charge_controller_asset_id_assets_id_fk" FOREIGN KEY ("charge_controller_asset_id") REFERENCES "public"."assets"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "power_systems" ADD CONSTRAINT "power_systems_ups_asset_id_assets_id_fk" FOREIGN KEY ("ups_asset_id") REFERENCES "public"."assets"("id") ON DELETE set null ON UPDATE cascade;