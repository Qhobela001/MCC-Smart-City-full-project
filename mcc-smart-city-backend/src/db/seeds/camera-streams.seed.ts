import { and, eq } from 'drizzle-orm';

import { db } from '../index';
import { cameras, cameraStreams } from '../schema';

type CameraStreamInsert = typeof cameraStreams.$inferInsert;

async function getCameraId(cameraCode: string): Promise<string> {
  const [camera] = await db
    .select({
      id: cameras.id,
    })
    .from(cameras)
    .where(eq(cameras.cameraCode, cameraCode))
    .limit(1);

  if (!camera) {
    throw new Error(
      `Camera "${cameraCode}" was not found. Run the cameras seed first.`,
    );
  }

  return camera.id;
}

async function insertStreamIfMissing(
  stream: CameraStreamInsert,
): Promise<void> {
  const [existingStream] = await db
    .select({
      id: cameraStreams.id,
    })
    .from(cameraStreams)
    .where(
      and(
        eq(cameraStreams.cameraId, stream.cameraId),
        eq(cameraStreams.name, stream.name),
      ),
    )
    .limit(1);

  if (existingStream) {
    return;
  }

  await db.insert(cameraStreams).values(stream);
}

export async function seedCameraStreams(): Promise<void> {
  console.log('Seeding camera streams...');

  const [fieldCameraOneId, fieldCameraTwoId] = await Promise.all([
    getCameraId('CAM-FIELD-001'),
    getCameraId('CAM-FIELD-002'),
  ]);

  const streamRecords: CameraStreamInsert[] = [
    /*
    |--------------------------------------------------------------------------
    | FIELD CAMERA 001
    |--------------------------------------------------------------------------
    */

    {
      cameraId: fieldCameraOneId,
      name: 'Field Camera 1 Main Stream',
      status: 'unavailable',
      purpose: 'recording',
      protocol: 'rtsp',
      streamUrl: null,
      resolutionWidth: 1920,
      resolutionHeight: 1080,
      framesPerSecond: 15,
      codec: 'h264',
      bitrateKbps: 4096,
      isPrimary: true,
      lastAvailableAt: null,
    },
    {
      cameraId: fieldCameraOneId,
      name: 'Field Camera 1 AI Stream',
      status: 'unavailable',
      purpose: 'ai_processing',
      protocol: 'rtsp',
      streamUrl: null,
      resolutionWidth: 640,
      resolutionHeight: 360,
      framesPerSecond: 10,
      codec: 'h264',
      bitrateKbps: 1024,
      isPrimary: false,
      lastAvailableAt: null,
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD CAMERA 002
    |--------------------------------------------------------------------------
    */

    {
      cameraId: fieldCameraTwoId,
      name: 'Field Camera 2 Main Stream',
      status: 'unavailable',
      purpose: 'recording',
      protocol: 'rtsp',
      streamUrl: null,
      resolutionWidth: 1920,
      resolutionHeight: 1080,
      framesPerSecond: 15,
      codec: 'h264',
      bitrateKbps: 4096,
      isPrimary: true,
      lastAvailableAt: null,
    },
    {
      cameraId: fieldCameraTwoId,
      name: 'Field Camera 2 AI Stream',
      status: 'unavailable',
      purpose: 'ai_processing',
      protocol: 'rtsp',
      streamUrl: null,
      resolutionWidth: 640,
      resolutionHeight: 360,
      framesPerSecond: 10,
      codec: 'h264',
      bitrateKbps: 1024,
      isPrimary: false,
      lastAvailableAt: null,
    },
  ];

  for (const stream of streamRecords) {
    await insertStreamIfMissing(stream);
  }

  console.log('Camera streams seeded.');
}
