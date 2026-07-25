CREATE TYPE "public"."incident_priority" AS ENUM('low', 'medium', 'high', 'critical');--> statement-breakpoint
CREATE TABLE "incident_categories" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"category_code" varchar(50) NOT NULL,
	"name" varchar(120) NOT NULL,
	"description" text,
	"display_order" integer DEFAULT 0 NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "incident_categories_category_code_unique" UNIQUE("category_code"),
	CONSTRAINT "incident_categories_name_unique" UNIQUE("name")
);
--> statement-breakpoint
CREATE TABLE "incident_types" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"category_id" uuid NOT NULL,
	"incident_type_code" varchar(60) NOT NULL,
	"name" varchar(160) NOT NULL,
	"description" text,
	"default_priority" "incident_priority" DEFAULT 'medium' NOT NULL,
	"responsible_department_id" uuid,
	"acknowledgement_target_minutes" integer,
	"response_target_minutes" integer,
	"resolution_target_minutes" integer,
	"is_ai_detectable" boolean DEFAULT false NOT NULL,
	"evidence_required" boolean DEFAULT true NOT NULL,
	"supervisor_verification_required" boolean DEFAULT true NOT NULL,
	"public_reporting_allowed" boolean DEFAULT false NOT NULL,
	"automatic_incident_creation_allowed" boolean DEFAULT false NOT NULL,
	"minimum_automatic_confidence" numeric(5, 4),
	"display_order" integer DEFAULT 0 NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "incident_types_incident_type_code_unique" UNIQUE("incident_type_code"),
	CONSTRAINT "incident_types_name_unique" UNIQUE("name")
);
--> statement-breakpoint
ALTER TABLE "incident_types" ADD CONSTRAINT "incident_types_category_id_incident_categories_id_fk" FOREIGN KEY ("category_id") REFERENCES "public"."incident_categories"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incident_types" ADD CONSTRAINT "incident_types_responsible_department_id_departments_id_fk" FOREIGN KEY ("responsible_department_id") REFERENCES "public"."departments"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
CREATE INDEX "incident_categories_code_idx" ON "incident_categories" USING btree ("category_code");--> statement-breakpoint
CREATE INDEX "incident_categories_name_idx" ON "incident_categories" USING btree ("name");--> statement-breakpoint
CREATE INDEX "incident_categories_active_idx" ON "incident_categories" USING btree ("is_active");--> statement-breakpoint
CREATE INDEX "incident_categories_display_order_idx" ON "incident_categories" USING btree ("display_order");--> statement-breakpoint
CREATE INDEX "incident_types_category_id_idx" ON "incident_types" USING btree ("category_id");--> statement-breakpoint
CREATE INDEX "incident_types_code_idx" ON "incident_types" USING btree ("incident_type_code");--> statement-breakpoint
CREATE INDEX "incident_types_name_idx" ON "incident_types" USING btree ("name");--> statement-breakpoint
CREATE INDEX "incident_types_priority_idx" ON "incident_types" USING btree ("default_priority");--> statement-breakpoint
CREATE INDEX "incident_types_department_id_idx" ON "incident_types" USING btree ("responsible_department_id");--> statement-breakpoint
CREATE INDEX "incident_types_active_idx" ON "incident_types" USING btree ("is_active");--> statement-breakpoint
CREATE INDEX "incident_types_ai_detectable_idx" ON "incident_types" USING btree ("is_ai_detectable");--> statement-breakpoint
CREATE INDEX "incident_types_category_active_idx" ON "incident_types" USING btree ("category_id","is_active");