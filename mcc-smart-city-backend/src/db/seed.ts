import 'dotenv/config';

import { seedRoles } from './seeds/roles.seed';
import { seedDepartments } from './seeds/departments.seed';
import { seedServiceLevelProfiles } from './seeds/service-level-profiles.seed';
import { seedIncidentCategories } from './seeds/incident-categories.seed';
import seedIncidentTypes from './seeds/incident-types.seed';
import { seedLocations } from './seeds/locations.seed';
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
import { seedIncidentNumberSequences } from './seeds/incident-number-sequences.seed';

async function seed(): Promise<void> {
  console.log('Starting database seed...');

  await seedRoles();
  await seedDepartments();

  await seedServiceLevelProfiles();
  await seedIncidentCategories();
  await seedServiceLevelProfiles();
  await seedIncidentCategories();
  await seedIncidentTypes();
  await seedIncidentNumberSequences();
  await seedIncidentTypes();

  await seedLocations();
  await seedAssets();
  await seedDevices();
  await seedCameras();
  await seedJetsonNodes();
  await seedNanoStations();
  await seedNetworkLinks();
  await seedCameraStreams();
  await seedPowerSystems();
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
