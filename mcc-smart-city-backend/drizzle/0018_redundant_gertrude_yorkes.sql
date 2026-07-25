CREATE TABLE "incidents" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"incident_number" varchar(40) NOT NULL,
	"external_reference" varchar(120),
	"parent_incident_id" uuid,
	"duplicate_of_incident_id" uuid,
	"incident_type_id" uuid NOT NULL,
	"category_id" uuid NOT NULL,
	"category_code_snapshot" varchar(50) NOT NULL,
	"category_name_snapshot" varchar(120) NOT NULL,
	"incident_type_code_snapshot" varchar(60) NOT NULL,
	"incident_type_name_snapshot" varchar(160) NOT NULL,
	"title" varchar(220) NOT NULL,
	"description" text,
	"severity" "incident_severity" DEFAULT 'moderate' NOT NULL,
	"priority" "incident_priority" DEFAULT 'medium' NOT NULL,
	"status" "incident_status" DEFAULT 'reported' NOT NULL,
	"source" "incident_source" DEFAULT 'manual' NOT NULL,
	"location_id" uuid,
	"location_name_snapshot" varchar(160),
	"address_snapshot" text,
	"district_snapshot" varchar(120),
	"latitude" numeric(10, 7),
	"longitude" numeric(10, 7),
	"location_accuracy_meters" numeric(10, 2),
	"reporter_user_id" uuid,
	"reporter_department_id" uuid,
	"reporter_name" varchar(160),
	"reporter_contact" varchar(160),
	"assigned_department_id" uuid,
	"assigned_user_id" uuid,
	"camera_id" uuid,
	"device_id" uuid,
	"camera_stream_id" uuid,
	"jetson_node_id" uuid,
	"camera_code_snapshot" varchar(80),
	"device_code_snapshot" varchar(80),
	"ai_confidence" numeric(5, 4),
	"ai_model_name" varchar(160),
	"ai_model_version" varchar(80),
	"detected_at" timestamp with time zone,
	"automatically_created" boolean DEFAULT false NOT NULL,
	"verification_required" boolean DEFAULT true NOT NULL,
	"risk_score" numeric(7, 2),
	"service_level_profile_id" uuid NOT NULL,
	"acknowledgement_target_minutes" integer NOT NULL,
	"response_target_minutes" integer NOT NULL,
	"resolution_target_minutes" integer NOT NULL,
	"escalation_after_minutes" integer,
	"acknowledgement_due_at" timestamp with time zone,
	"response_due_at" timestamp with time zone,
	"resolution_due_at" timestamp with time zone,
	"escalation_due_at" timestamp with time zone,
	"reported_at" timestamp with time zone DEFAULT now() NOT NULL,
	"verified_at" timestamp with time zone,
	"acknowledged_at" timestamp with time zone,
	"assigned_at" timestamp with time zone,
	"work_started_at" timestamp with time zone,
	"resolved_at" timestamp with time zone,
	"closed_at" timestamp with time zone,
	"cancelled_at" timestamp with time zone,
	"resolution_code" "incident_resolution",
	"resolution_summary" text,
	"closure_reason" text,
	"cancellation_reason" text,
	"closed_by_user_id" uuid,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "incidents_incident_number_unique" UNIQUE("incident_number")
);
--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_parent_incident_id_incidents_id_fk" FOREIGN KEY ("parent_incident_id") REFERENCES "public"."incidents"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_duplicate_of_incident_id_incidents_id_fk" FOREIGN KEY ("duplicate_of_incident_id") REFERENCES "public"."incidents"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_incident_type_id_incident_types_id_fk" FOREIGN KEY ("incident_type_id") REFERENCES "public"."incident_types"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_category_id_incident_categories_id_fk" FOREIGN KEY ("category_id") REFERENCES "public"."incident_categories"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_location_id_locations_id_fk" FOREIGN KEY ("location_id") REFERENCES "public"."locations"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_reporter_user_id_users_id_fk" FOREIGN KEY ("reporter_user_id") REFERENCES "public"."users"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_reporter_department_id_departments_id_fk" FOREIGN KEY ("reporter_department_id") REFERENCES "public"."departments"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_assigned_department_id_departments_id_fk" FOREIGN KEY ("assigned_department_id") REFERENCES "public"."departments"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_assigned_user_id_users_id_fk" FOREIGN KEY ("assigned_user_id") REFERENCES "public"."users"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_camera_id_cameras_id_fk" FOREIGN KEY ("camera_id") REFERENCES "public"."cameras"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_device_id_devices_id_fk" FOREIGN KEY ("device_id") REFERENCES "public"."devices"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_camera_stream_id_camera_streams_id_fk" FOREIGN KEY ("camera_stream_id") REFERENCES "public"."camera_streams"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_jetson_node_id_jetson_nodes_id_fk" FOREIGN KEY ("jetson_node_id") REFERENCES "public"."jetson_nodes"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_service_level_profile_id_service_level_profiles_id_fk" FOREIGN KEY ("service_level_profile_id") REFERENCES "public"."service_level_profiles"("id") ON DELETE restrict ON UPDATE cascade;--> statement-breakpoint
ALTER TABLE "incidents" ADD CONSTRAINT "incidents_closed_by_user_id_users_id_fk" FOREIGN KEY ("closed_by_user_id") REFERENCES "public"."users"("id") ON DELETE set null ON UPDATE cascade;--> statement-breakpoint
CREATE INDEX "incidents_external_reference_idx" ON "incidents" USING btree ("external_reference");--> statement-breakpoint
CREATE INDEX "incidents_parent_incident_id_idx" ON "incidents" USING btree ("parent_incident_id");--> statement-breakpoint
CREATE INDEX "incidents_duplicate_of_incident_id_idx" ON "incidents" USING btree ("duplicate_of_incident_id");--> statement-breakpoint
CREATE INDEX "incidents_incident_type_id_idx" ON "incidents" USING btree ("incident_type_id");--> statement-breakpoint
CREATE INDEX "incidents_category_id_idx" ON "incidents" USING btree ("category_id");--> statement-breakpoint
CREATE INDEX "incidents_status_idx" ON "incidents" USING btree ("status");--> statement-breakpoint
CREATE INDEX "incidents_priority_idx" ON "incidents" USING btree ("priority");--> statement-breakpoint
CREATE INDEX "incidents_severity_idx" ON "incidents" USING btree ("severity");--> statement-breakpoint
CREATE INDEX "incidents_source_idx" ON "incidents" USING btree ("source");--> statement-breakpoint
CREATE INDEX "incidents_location_id_idx" ON "incidents" USING btree ("location_id");--> statement-breakpoint
CREATE INDEX "incidents_reporter_user_id_idx" ON "incidents" USING btree ("reporter_user_id");--> statement-breakpoint
CREATE INDEX "incidents_assigned_department_id_idx" ON "incidents" USING btree ("assigned_department_id");--> statement-breakpoint
CREATE INDEX "incidents_assigned_user_id_idx" ON "incidents" USING btree ("assigned_user_id");--> statement-breakpoint
CREATE INDEX "incidents_camera_id_idx" ON "incidents" USING btree ("camera_id");--> statement-breakpoint
CREATE INDEX "incidents_device_id_idx" ON "incidents" USING btree ("device_id");--> statement-breakpoint
CREATE INDEX "incidents_camera_stream_id_idx" ON "incidents" USING btree ("camera_stream_id");--> statement-breakpoint
CREATE INDEX "incidents_jetson_node_id_idx" ON "incidents" USING btree ("jetson_node_id");--> statement-breakpoint
CREATE INDEX "incidents_service_level_profile_id_idx" ON "incidents" USING btree ("service_level_profile_id");--> statement-breakpoint
CREATE INDEX "incidents_reported_at_idx" ON "incidents" USING btree ("reported_at");--> statement-breakpoint
CREATE INDEX "incidents_acknowledgement_due_at_idx" ON "incidents" USING btree ("acknowledgement_due_at");--> statement-breakpoint
CREATE INDEX "incidents_response_due_at_idx" ON "incidents" USING btree ("response_due_at");--> statement-breakpoint
CREATE INDEX "incidents_resolution_due_at_idx" ON "incidents" USING btree ("resolution_due_at");--> statement-breakpoint
CREATE INDEX "incidents_escalation_due_at_idx" ON "incidents" USING btree ("escalation_due_at");--> statement-breakpoint
CREATE INDEX "incidents_status_priority_idx" ON "incidents" USING btree ("status","priority");--> statement-breakpoint
CREATE INDEX "incidents_department_status_idx" ON "incidents" USING btree ("assigned_department_id","status");--> statement-breakpoint
CREATE INDEX "incidents_type_reported_at_idx" ON "incidents" USING btree ("incident_type_id","reported_at");--> statement-breakpoint
CREATE INDEX "incidents_status_reported_at_idx" ON "incidents" USING btree ("status","reported_at");