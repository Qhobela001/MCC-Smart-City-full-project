ALTER TABLE "devices" DROP CONSTRAINT "devices_asset_id_assets_id_fk";
--> statement-breakpoint
ALTER TABLE "devices" ADD CONSTRAINT "devices_asset_id_assets_id_fk" FOREIGN KEY ("asset_id") REFERENCES "public"."assets"("id") ON DELETE restrict ON UPDATE cascade;