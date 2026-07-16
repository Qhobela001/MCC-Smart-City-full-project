CREATE TABLE "camera_stream_metrics" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"camera_stream_id" uuid NOT NULL,
	"frames_per_second" numeric(8, 3),
	"bitrate_kbps" integer,
	"latency_ms" numeric(10, 3),
	"frame_drop_percent" numeric(5, 2),
	"packet_loss_percent" numeric(5, 2),
	"jitter_ms" numeric(10, 3),
	"width" integer,
	"height" integer,
	"is_reachable" boolean DEFAULT false NOT NULL,
	"is_decoding" boolean DEFAULT false NOT NULL,
	"last_frame_at" timestamp with time zone,
	"recorded_at" timestamp with time zone DEFAULT now() NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "camera_stream_metrics" ADD CONSTRAINT "camera_stream_metrics_camera_stream_id_camera_streams_id_fk" FOREIGN KEY ("camera_stream_id") REFERENCES "public"."camera_streams"("id") ON DELETE cascade ON UPDATE cascade;