import { eq } from 'drizzle-orm';

import { db } from '../index';
import { devices, networkLinks } from '../schema';

type NetworkLinkInsert = typeof networkLinks.$inferInsert;

async function getDeviceId(deviceCode: string): Promise<string> {
  const [device] = await db
    .select({
      id: devices.id,
    })
    .from(devices)
    .where(eq(devices.deviceCode, deviceCode))
    .limit(1);

  if (!device) {
    throw new Error(
      `Device "${deviceCode}" was not found. Run the devices seed first.`,
    );
  }

  return device.id;
}

export async function seedNetworkLinks(): Promise<void> {
  console.log('Seeding network links...');

  const [hqNanoOneId, hqNanoTwoId, fieldNanoOneId, fieldNanoTwoId] =
    await Promise.all([
      getDeviceId('DEV-NANO-HQ-001'),
      getDeviceId('DEV-NANO-HQ-002'),
      getDeviceId('DEV-NANO-FIELD-001'),
      getDeviceId('DEV-NANO-FIELD-002'),
    ]);

  const networkLinkRecords: NetworkLinkInsert[] = [
    {
      linkCode: 'LINK-WIRELESS-FIELD-001-HQ-001',
      name: 'Field Site 1 to MCC HQ Wireless Backhaul',
      type: 'point_to_point',
      status: 'offline',
      sourceDeviceId: fieldNanoOneId,
      destinationDeviceId: hqNanoOneId,
      distanceMeters: 5000,
      frequencyMhz: 5805,
      channelWidthMhz: 40,
      expectedCapacityMbps: '100.00',
      lastCheckedAt: null,
      metadata: {
        deploymentState: 'planned',
        topology: 'point_to_point',
        frequencyBand: '5GHz',
        airmaxEnabled: true,
        lineOfSightRequired: true,
        lineOfSightVerified: false,
        sourceRole: 'station',
        destinationRole: 'access_point',
        expectedUse: [
          'camera_video_stream',
          'device_telemetry',
          'remote_management',
        ],
        notes:
          'Primary wireless backhaul between Field Site 1 and MCC Headquarters.',
      },
    },
    {
      linkCode: 'LINK-WIRELESS-FIELD-002-HQ-002',
      name: 'Field Site 2 to MCC HQ Wireless Backhaul',
      type: 'point_to_point',
      status: 'offline',
      sourceDeviceId: fieldNanoTwoId,
      destinationDeviceId: hqNanoTwoId,
      distanceMeters: 5000,
      frequencyMhz: 5825,
      channelWidthMhz: 40,
      expectedCapacityMbps: '100.00',
      lastCheckedAt: null,
      metadata: {
        deploymentState: 'planned',
        topology: 'point_to_point',
        frequencyBand: '5GHz',
        airmaxEnabled: true,
        lineOfSightRequired: true,
        lineOfSightVerified: false,
        sourceRole: 'station',
        destinationRole: 'access_point',
        expectedUse: [
          'camera_video_stream',
          'device_telemetry',
          'remote_management',
        ],
        notes:
          'Primary wireless backhaul between Field Site 2 and MCC Headquarters.',
      },
    },
  ];

  await db
    .insert(networkLinks)
    .values(networkLinkRecords)
    .onConflictDoNothing();

  console.log('Network links seeded.');
}
