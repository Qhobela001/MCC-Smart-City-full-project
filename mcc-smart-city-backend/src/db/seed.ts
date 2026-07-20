import 'dotenv/config';
import { seedDepartments } from './seeds/departments.seed';
import { seedLocations } from './seeds/locations.seed';
import { seedRoles } from './seeds/roles.seed';
import { seedAssets } from './seeds/assets.seed';
import { seedDevices } from './seeds/devices.seed';
import { seedCameras } from './seeds/cameras.seed';
import { seedJetsonNodes } from './seeds/jetson-nodes.seed';
import { seedNanoStations } from './seeds/nanostations.seed';
import { seedNetworkLinks } from './seeds/network-links.seed';
import { seedCameraStreams } from './seeds/camera-streams.seed';
import { seedPowerSystems } from './seeds/power-systems.seed';
import { seedDeviceHeartbeats } from './seeds/device-heartbeats.seed';
import { seedDeviceMetrics } from './seeds/device-metrics.seed';
import { seedDeviceEvents } from './seeds/device-events.seed';
import { seedNetworkLinkMetrics } from './seeds/network-link-metrics.seed';
import { seedPowerReadings } from './seeds/power-readings.seed';
import { seedCameraStreamMetrics } from './seeds/camera-stream-metrics.seed';

async function seed(): Promise<void> {
  console.log('Starting database seed...');

  await seedRoles();
  await seedDepartments();
  await seedLocations();
  await seedAssets();
  await seedDevices();
  await seedCameras();
  await seedJetsonNodes();
  await seedNanoStations();
  await seedNetworkLinks();
  await seedCameraStreams();
  await seedPowerSystems();
  await seedDeviceEvents();
  await seedDeviceHeartbeats();
  await seedDeviceMetrics();
  await seedDeviceEvents();
  await seedNetworkLinkMetrics();
  await seedPowerReadings();
  await seedCameraStreamMetrics();

  console.log('Database seed completed successfully.');
}

seed().catch((error: unknown) => {
  console.error('Database seed failed:', error);
  process.exitCode = 1;
});
