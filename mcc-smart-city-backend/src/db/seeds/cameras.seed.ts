import { eq } from 'drizzle-orm';

import { db } from '../index';
import { cameras, devices } from '../schema';

async function getDevice(deviceCode: string): Promise<{
  id: string;
  name: string;
}> {
  const [device] = await db
    .select({
      id: devices.id,
      name: devices.name,
    })
    .from(devices)
    .where(eq(devices.deviceCode, deviceCode))
    .limit(1);

  if (!device) {
    throw new Error(
      `Device "${deviceCode}" was not found. Run the device seed first.`,
    );
  }

  return device;
}

export async function seedCameras(): Promise<void> {
  console.log('Seeding cameras...');

  const jetson = await getDevice('DEV-JETSON-HQ-001');

  const fieldCameraOne = await getDevice('DEV-CAMERA-FIELD-001');
  const fieldCameraTwo = await getDevice('DEV-CAMERA-FIELD-002');

  await db
    .insert(cameras)
    .values([
      {
        deviceId: fieldCameraOne.id,

        cameraCode: 'CAM-FIELD-001',

        rtspUrl: 'rtsp://admin:password@192.168.20.11:554/live/main',

        streamPath: '/live/main',

        streamUsername: 'admin',

        isAiEnabled: true,

        isRecordingEnabled: true,

        assignedJetsonId: jetson.id,

        fieldOfViewDescription:
          'Pioneer Road intersection. Covers road traffic, pedestrians, illegal dumping hotspot and surrounding sidewalks.',
      },

      {
        deviceId: fieldCameraTwo.id,

        cameraCode: 'CAM-FIELD-002',

        rtspUrl: 'rtsp://admin:password@192.168.30.11:554/live/main',

        streamPath: '/live/main',

        streamUsername: 'admin',

        isAiEnabled: true,

        isRecordingEnabled: true,

        assignedJetsonId: jetson.id,

        fieldOfViewDescription:
          'Kingsway CBD monitoring point covering public spaces, traffic flow and municipal infrastructure.',
      },
    ])
    .onConflictDoNothing();

  console.log('Cameras seeded.');
}
