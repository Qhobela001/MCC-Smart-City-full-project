import { and, eq } from 'drizzle-orm';

import { db } from '../index';
import { deviceEvents, devices } from '../schema';

type DeviceEventInsert = typeof deviceEvents.$inferInsert;

interface DeviceEventSeedRecord {
  deviceCode: string;
  eventType: string;
  severity: DeviceEventInsert['severity'];
  title: string;
  description: string;
  occurredAt: Date;
  resolvedAt?: Date | null;
  acknowledgedAt?: Date | null;
  metadata?: Record<string, unknown>;
}

/*
|--------------------------------------------------------------------------
| Deterministic timestamps
|--------------------------------------------------------------------------
|
| Fixed timestamps prevent duplicate seed records when the seed command
| is executed multiple times.
|
*/

const EVENT_TIMESTAMPS = {
  jetsonStarted: new Date('2026-07-20T07:00:00.000Z'),
  aiServiceStarted: new Date('2026-07-20T07:02:00.000Z'),
  serverStarted: new Date('2026-07-20T06:30:00.000Z'),
  switchStarted: new Date('2026-07-20T06:35:00.000Z'),
  upsSelfTest: new Date('2026-07-20T06:40:00.000Z'),

  nanoHq1Connected: new Date('2026-07-20T07:10:00.000Z'),
  nanoHq2Connected: new Date('2026-07-20T07:11:00.000Z'),
  nanoHq3Standby: new Date('2026-07-20T07:12:00.000Z'),
  nanoHq4Standby: new Date('2026-07-20T07:13:00.000Z'),

  camera1Connected: new Date('2026-07-20T07:20:00.000Z'),
  camera1StreamStarted: new Date('2026-07-20T07:21:00.000Z'),
  nanoField1Connected: new Date('2026-07-20T07:19:00.000Z'),

  camera2Connected: new Date('2026-07-20T07:30:00.000Z'),
  camera2StreamStarted: new Date('2026-07-20T07:31:00.000Z'),
  nanoField2Connected: new Date('2026-07-20T07:29:00.000Z'),
} as const;

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

async function eventExists(
  deviceId: string,
  eventType: string,
  occurredAt: Date,
): Promise<boolean> {
  const [existingEvent] = await db
    .select({
      id: deviceEvents.id,
    })
    .from(deviceEvents)
    .where(
      and(
        eq(deviceEvents.deviceId, deviceId),
        eq(deviceEvents.eventType, eventType),
        eq(deviceEvents.occurredAt, occurredAt),
      ),
    )
    .limit(1);

  return Boolean(existingEvent);
}

async function insertDeviceEvent(record: DeviceEventSeedRecord): Promise<void> {
  const deviceId = await getDeviceId(record.deviceCode);

  const alreadyExists = await eventExists(
    deviceId,
    record.eventType,
    record.occurredAt,
  );

  if (alreadyExists) {
    return;
  }

  const event: DeviceEventInsert = {
    deviceId,
    eventType: record.eventType,
    severity: record.severity,
    title: record.title,
    description: record.description,
    occurredAt: record.occurredAt,
    resolvedAt: record.resolvedAt ?? null,
    acknowledgedAt: record.acknowledgedAt ?? null,
    acknowledgedByUserId: null,
    metadata: {
      source: 'database_seed',
      seededDeviceCode: record.deviceCode,
      ...record.metadata,
    },
  };

  await db.insert(deviceEvents).values(event);
}

export async function seedDeviceEvents(): Promise<void> {
  console.log('Seeding device events...');

  const eventRecords: DeviceEventSeedRecord[] = [
    /*
    |--------------------------------------------------------------------------
    | JETSON ORIN NANO
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-JETSON-HQ-001',
      eventType: 'device_started',
      severity: 'info',
      title: 'Jetson processing node started',
      description:
        'The NVIDIA Jetson Orin Nano processing node completed its startup sequence.',
      occurredAt: EVENT_TIMESTAMPS.jetsonStarted,
      metadata: {
        category: 'system',
        component: 'jetson',
        hostname: 'mcc-jetson-01',
      },
    },
    {
      deviceCode: 'DEV-JETSON-HQ-001',
      eventType: 'ai_service_started',
      severity: 'info',
      title: 'AI video analytics service started',
      description:
        'The Jetson AI inference service started and is ready to process camera streams.',
      occurredAt: EVENT_TIMESTAMPS.aiServiceStarted,
      metadata: {
        category: 'ai',
        service: 'video_analytics',
        workloadStatus: 'ready',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | HQ SERVER AND NETWORK INFRASTRUCTURE
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-SERVER-HQ-001',
      eventType: 'service_started',
      severity: 'info',
      title: 'MCC application services started',
      description:
        'The backend API, database connectivity and storage services started successfully.',
      occurredAt: EVENT_TIMESTAMPS.serverStarted,
      metadata: {
        category: 'system',
        services: ['api', 'database', 'storage'],
      },
    },
    {
      deviceCode: 'DEV-SWITCH-HQ-001',
      eventType: 'device_started',
      severity: 'info',
      title: 'HQ managed network switch started',
      description:
        'The MCC headquarters managed switch became available to connected infrastructure.',
      occurredAt: EVENT_TIMESTAMPS.switchStarted,
      metadata: {
        category: 'network',
        managed: true,
      },
    },
    {
      deviceCode: 'DEV-UPS-HQ-001',
      eventType: 'self_test_completed',
      severity: 'info',
      title: 'UPS self-test completed',
      description:
        'The headquarters backup power unit completed its startup self-test.',
      occurredAt: EVENT_TIMESTAMPS.upsSelfTest,
      resolvedAt: EVENT_TIMESTAMPS.upsSelfTest,
      metadata: {
        category: 'power',
        result: 'passed',
        batteryStatus: 'normal',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | HQ NANOSTATIONS
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-NANO-HQ-001',
      eventType: 'wireless_peer_connected',
      severity: 'info',
      title: 'Field Site 1 wireless link established',
      description:
        'The headquarters NanoStation established a wireless bridge connection with Field Site 1.',
      occurredAt: EVENT_TIMESTAMPS.nanoHq1Connected,
      metadata: {
        category: 'network',
        peerDeviceCode: 'DEV-NANO-FIELD-001',
        networkLinkCode: 'LINK-FIELD-001',
        frequencyBand: '5GHz',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-002',
      eventType: 'wireless_peer_connected',
      severity: 'info',
      title: 'Field Site 2 wireless link established',
      description:
        'The headquarters NanoStation established a wireless bridge connection with Field Site 2.',
      occurredAt: EVENT_TIMESTAMPS.nanoHq2Connected,
      metadata: {
        category: 'network',
        peerDeviceCode: 'DEV-NANO-FIELD-002',
        networkLinkCode: 'LINK-FIELD-002',
        frequencyBand: '5GHz',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-003',
      eventType: 'standby_mode_enabled',
      severity: 'info',
      title: 'NanoStation placed in standby mode',
      description:
        'The NanoStation is reserved for a future field deployment and is currently operating in standby mode.',
      occurredAt: EVENT_TIMESTAMPS.nanoHq3Standby,
      metadata: {
        category: 'network',
        deploymentState: 'standby',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-004',
      eventType: 'standby_mode_enabled',
      severity: 'info',
      title: 'NanoStation placed in standby mode',
      description:
        'The NanoStation is reserved for a future field deployment and is currently operating in standby mode.',
      occurredAt: EVENT_TIMESTAMPS.nanoHq4Standby,
      metadata: {
        category: 'network',
        deploymentState: 'standby',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 001
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-NANO-FIELD-001',
      eventType: 'wireless_peer_connected',
      severity: 'info',
      title: 'Field Site 1 uplink established',
      description:
        'The field NanoStation established a wireless bridge connection with MCC headquarters.',
      occurredAt: EVENT_TIMESTAMPS.nanoField1Connected,
      metadata: {
        category: 'network',
        peerDeviceCode: 'DEV-NANO-HQ-001',
        networkLinkCode: 'LINK-FIELD-001',
        poweredBy: 'PWR-FIELD-001',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-001',
      eventType: 'device_connected',
      severity: 'info',
      title: 'Field Camera 1 connected',
      description:
        'The Field Site 1 PTZ camera connected to the MCC monitoring network.',
      occurredAt: EVENT_TIMESTAMPS.camera1Connected,
      metadata: {
        category: 'camera',
        cameraCode: 'CAM-FIELD-001',
        model: 'V380 SC31 PTZ',
        poweredBy: 'PWR-FIELD-001',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-001',
      eventType: 'stream_started',
      severity: 'info',
      title: 'Field Camera 1 stream started',
      description:
        'The primary video stream for Field Camera 1 became available for monitoring.',
      occurredAt: EVENT_TIMESTAMPS.camera1StreamStarted,
      metadata: {
        category: 'video',
        cameraCode: 'CAM-FIELD-001',
        protocol: 'rtsp',
        purpose: 'recording',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 002
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-NANO-FIELD-002',
      eventType: 'wireless_peer_connected',
      severity: 'info',
      title: 'Field Site 2 uplink established',
      description:
        'The field NanoStation established a wireless bridge connection with MCC headquarters.',
      occurredAt: EVENT_TIMESTAMPS.nanoField2Connected,
      metadata: {
        category: 'network',
        peerDeviceCode: 'DEV-NANO-HQ-002',
        networkLinkCode: 'LINK-FIELD-002',
        poweredBy: 'PWR-FIELD-002',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-002',
      eventType: 'device_connected',
      severity: 'info',
      title: 'Field Camera 2 connected',
      description:
        'The Field Site 2 PTZ camera connected to the MCC monitoring network.',
      occurredAt: EVENT_TIMESTAMPS.camera2Connected,
      metadata: {
        category: 'camera',
        cameraCode: 'CAM-FIELD-002',
        model: 'V380 SC31 PTZ',
        poweredBy: 'PWR-FIELD-002',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-002',
      eventType: 'stream_started',
      severity: 'info',
      title: 'Field Camera 2 stream started',
      description:
        'The primary video stream for Field Camera 2 became available for monitoring.',
      occurredAt: EVENT_TIMESTAMPS.camera2StreamStarted,
      metadata: {
        category: 'video',
        cameraCode: 'CAM-FIELD-002',
        protocol: 'rtsp',
        purpose: 'recording',
      },
    },
  ];

  for (const eventRecord of eventRecords) {
    await insertDeviceEvent(eventRecord);
  }

  console.log(`Device events seeded: ${eventRecords.length} records.`);
}
