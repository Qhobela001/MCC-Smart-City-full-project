CREATE TABLE "network_link_metrics" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"network_link_id" uuid NOT NULL,
	"signal_strength_dbm" numeric(6, 2),
	"noise_floor_dbm" numeric(6, 2),
	"signal_to_noise_ratio_db" numeric(6, 2),
	"transmit_capacity_mbps" numeric(10, 2),
	"receive_capacity_mbps" numeric(10, 2),
	"transmit_throughput_mbps" numeric(10, 2),
	"receive_throughput_mbps" numeric(10, 2),
	"latency_ms" numeric(10, 3),
	"packet_loss_percent" numeric(5, 2),
	"airmax_quality_percent" numeric(5, 2),
	"airmax_capacity_percent" numeric(5, 2),
	"connection_count" integer,
	"recorded_at" timestamp with time zone DEFAULT now() NOT NULL,
	"metadata" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "network_link_metrics" ADD CONSTRAINT "network_link_metrics_network_link_id_network_links_id_fk" FOREIGN KEY ("network_link_id") REFERENCES "public"."network_links"("id") ON DELETE cascade ON UPDATE cascade;