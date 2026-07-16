CREATE TABLE "power_readings" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"power_system_id" uuid NOT NULL,
	"solar_voltage" numeric(8, 3),
	"solar_current_amps" numeric(8, 3),
	"solar_power_watts" numeric(10, 3),
	"battery_voltage" numeric(8, 3),
	"battery_current_amps" numeric(8, 3),
	"battery_state_of_charge_percent" numeric(5, 2),
	"battery_temperature_celsius" numeric(6, 2),
	"load_voltage" numeric(8, 3),
	"load_current_amps" numeric(8, 3),
	"load_power_watts" numeric(10, 3),
	"estimated_runtime_minutes" integer,
	"charging_state" varchar(40),
	"controller_temperature_celsius" numeric(6, 2),
	"recorded_at" timestamp with time zone DEFAULT now() NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "power_readings" ADD CONSTRAINT "power_readings_power_system_id_power_systems_id_fk" FOREIGN KEY ("power_system_id") REFERENCES "public"."power_systems"("id") ON DELETE cascade ON UPDATE cascade;