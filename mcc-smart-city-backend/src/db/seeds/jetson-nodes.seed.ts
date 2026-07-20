import { eq } from 'drizzle-orm';

import { db } from '../index';
import { devices, jetsonNodes } from '../schema';

type JetsonNodeInsert = typeof jetsonNodes.$inferInsert;

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

export async function seedJetsonNodes(): Promise<void> {
  console.log('Seeding Jetson nodes...');

  const jetsonDeviceId = await getDeviceId('DEV-JETSON-HQ-001');

  const jetsonNodeRecords: JetsonNodeInsert[] = [
    {
      deviceId: jetsonDeviceId,

      hostname: 'mcc-jetson-hq-001',

      jetpackVersion: null,

      cudaVersion: null,

      tensorrtVersion: null,

      pythonVersion: '3.10',

      workloadStatus: 'idle',

      maximumCameraStreams: 4,

      activeCameraStreams: 0,

      aiServiceVersion: '0.1.0',

      lastModelSyncAt: null,
    },
  ];

  await db.insert(jetsonNodes).values(jetsonNodeRecords).onConflictDoNothing();

  console.log('Jetson nodes seeded.');
}
