CREATE TYPE "public"."incident_source" AS ENUM('ai_detection', 'camera_operator', 'citizen_web', 'citizen_mobile', 'iot_sensor', 'control_room', 'manual', 'api');--> statement-breakpoint
CREATE TYPE "public"."incident_status" AS ENUM('reported', 'verified', 'acknowledged', 'assigned', 'in_progress', 'awaiting_external', 'resolved', 'closed', 'cancelled', 'duplicate');--> statement-breakpoint
CREATE TABLE "incident_number_sequences" (
	"year" integer PRIMARY KEY NOT NULL,
	"prefix" varchar(20) DEFAULT 'INC' NOT NULL,
	"last_number" integer DEFAULT 0 NOT NULL,
	"padding_length" integer DEFAULT 6 NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX "incident_number_sequences_updated_at_idx" ON "incident_number_sequences" USING btree ("updated_at");