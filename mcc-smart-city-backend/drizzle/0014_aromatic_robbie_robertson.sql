CREATE TABLE "service_level_profiles" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"profile_code" varchar(60) NOT NULL,
	"name" varchar(160) NOT NULL,
	"description" text,
	"acknowledgement_target_minutes" integer NOT NULL,
	"response_target_minutes" integer NOT NULL,
	"resolution_target_minutes" integer NOT NULL,
	"escalation_after_minutes" integer,
	"is_active" boolean DEFAULT true NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "service_level_profiles_profile_code_unique" UNIQUE("profile_code"),
	CONSTRAINT "service_level_profiles_name_unique" UNIQUE("name")
);
--> statement-breakpoint
ALTER TABLE "incident_types" ADD COLUMN "service_level_profile_id" uuid NOT NULL;--> statement-breakpoint
CREATE INDEX "service_level_profiles_active_idx" ON "service_level_profiles" USING btree ("is_active");--> statement-breakpoint
CREATE INDEX "service_level_profiles_ack_target_idx" ON "service_level_profiles" USING btree ("acknowledgement_target_minutes");--> statement-breakpoint
CREATE INDEX "service_level_profiles_resolution_target_idx" ON "service_level_profiles" USING btree ("resolution_target_minutes");--> statement-breakpoint
ALTER TABLE "incident_types" ADD CONSTRAINT "incident_types_service_level_profile_id_service_level_profiles_id_fk" FOREIGN KEY ("service_level_profile_id") REFERENCES "public"."service_level_profiles"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
CREATE INDEX "incident_types_service_level_profile_id_idx" ON "incident_types" USING btree ("service_level_profile_id");--> statement-breakpoint
ALTER TABLE "incident_types" DROP COLUMN "acknowledgement_target_minutes";--> statement-breakpoint
ALTER TABLE "incident_types" DROP COLUMN "response_target_minutes";--> statement-breakpoint
ALTER TABLE "incident_types" DROP COLUMN "resolution_target_minutes";