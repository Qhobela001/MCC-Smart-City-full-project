CREATE TYPE "public"."asset_status" AS ENUM('planned', 'installed', 'operational', 'maintenance', 'retired');--> statement-breakpoint
CREATE TYPE "public"."asset_type" AS ENUM('camera', 'jetson', 'nanostation', 'pole', 'cabinet', 'solar_panel', 'battery', 'charge_controller', 'ups', 'network_switch', 'server', 'other');--> statement-breakpoint
CREATE TABLE "assets" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"asset_code" varchar(80) NOT NULL,
	"asset_name" varchar(160) NOT NULL,
	"asset_type" "asset_type" NOT NULL,
	"status" "asset_status" DEFAULT 'planned' NOT NULL,
	"manufacturer" varchar(120),
	"model" varchar(120),
	"serial_number" varchar(120),
	"purchase_date" timestamp with time zone,
	"installation_date" timestamp with time zone,
	"warranty_expiry" timestamp with time zone,
	"expected_life_years" integer,
	"location_id" uuid,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "assets_asset_code_unique" UNIQUE("asset_code")
);
--> statement-breakpoint
ALTER TABLE "devices" ADD COLUMN "asset_id" uuid NOT NULL;--> statement-breakpoint
ALTER TABLE "assets" ADD CONSTRAINT "assets_location_id_locations_id_fk" FOREIGN KEY ("location_id") REFERENCES "public"."locations"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "devices" ADD CONSTRAINT "devices_asset_id_assets_id_fk" FOREIGN KEY ("asset_id") REFERENCES "public"."assets"("id") ON DELETE cascade ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "devices" ADD CONSTRAINT "devices_asset_id_unique" UNIQUE("asset_id");