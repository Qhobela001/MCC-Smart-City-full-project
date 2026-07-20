import { and, eq } from 'drizzle-orm';

import { db } from '../index';
import { cameraStreamMetrics, cameraStreams } from '../schema';

type CameraStreamMetricInsert = typeof cameraStreamMetrics.$inferInsert;

/*
|--------------------------------------------------------------------------
| Deterministic baseline timestamp
|--------------------------------------------------------------------------
|
| A fixed timestamp makes the seed idempotent. Running the seed repeatedly
| will not create duplicate baseline measurements for the same stream.
|
*/

const SEED_RECORDED_AT = new Date('2026-07-20T08:00:00.000Z');

const SEED_LAST_FRAME_AT = new Date('2026-07-20T07:59:59.850Z');

async function metricExists(
  cameraStreamId: string,
  recordedAt: Date,
): Promise<boolean> {
  const [existingMetric] = await db
    .select({
      id: cameraStreamMetrics.id,
    })
    .from(cameraStreamMetrics)
    .where(
      and(
        eq(cameraStreamMetrics.cameraStreamId, cameraStreamId),
        eq(cameraStreamMetrics.recordedAt, recordedAt),
      ),
    )
    .limit(1);

  return Boolean(existingMetric);
}

function buildMetric(
  cameraStreamId: string,
  streamIndex: number,
): CameraStreamMetricInsert {
  /*
  |--------------------------------------------------------------------------
  | Stream profiles
  |--------------------------------------------------------------------------
  |
  | The camera-stream seed currently creates two streams per camera.
  |
  | Even-numbered entries use a higher-quality recording profile.
  | Odd-numbered entries use a lower-latency AI-processing profile.
  |
  */

  const isRecordingProfile = streamIndex % 2 === 0;

  if (isRecordingProfile) {
    return {
      cameraStreamId,

      framesPerSecond: '25.000',
      bitrateKbps: 4096,

      latencyMs: '82.500',
      frameDropPercent: '0.18',
      packetLossPercent: '0.12',
      jitterMs: '3.240',

      width: 2560,
      height: 1440,

      isReachable: true,
      isDecoding: true,

      lastFrameAt: SEED_LAST_FRAME_AT,
      recordedAt: SEED_RECORDED_AT,

      metadata: {
        source: 'database_seed',
        baselineMeasurement: true,
        streamProfile: 'recording',
        codec: 'H.265',
        transport: 'RTSP',
        healthCondition: 'healthy',
      },
    };
  }

  return {
    cameraStreamId,

    framesPerSecond: '20.000',
    bitrateKbps: 2048,

    latencyMs: '64.300',
    frameDropPercent: '0.24',
    packetLossPercent: '0.15',
    jitterMs: '2.870',

    width: 1920,
    height: 1080,

    isReachable: true,
    isDecoding: true,

    lastFrameAt: SEED_LAST_FRAME_AT,
    recordedAt: SEED_RECORDED_AT,

    metadata: {
      source: 'database_seed',
      baselineMeasurement: true,
      streamProfile: 'ai_processing',
      codec: 'H.264',
      transport: 'RTSP',
      consumer: 'jetson_inference_pipeline',
      healthCondition: 'healthy',
    },
  };
}

export async function seedCameraStreamMetrics(): Promise<void> {
  console.log('Seeding camera stream metrics...');

  const existingStreams = await db
    .select({
      id: cameraStreams.id,
    })
    .from(cameraStreams);

  if (existingStreams.length === 0) {
    throw new Error(
      'No camera streams were found. Run the camera-streams seed first.',
    );
  }

  let insertedCount = 0;
  let skippedCount = 0;

  for (const [index, stream] of existingStreams.entries()) {
    const alreadyExists = await metricExists(stream.id, SEED_RECORDED_AT);

    if (alreadyExists) {
      skippedCount += 1;
      continue;
    }

    const metric = buildMetric(stream.id, index);

    await db.insert(cameraStreamMetrics).values(metric);

    insertedCount += 1;
  }

  console.log(
    `Camera stream metrics seeded: ${insertedCount} inserted, ${skippedCount} already existed.`,
  );
}
