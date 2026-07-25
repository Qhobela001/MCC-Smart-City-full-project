import { eq } from 'drizzle-orm';

import { db } from '../index';
import { deviceHeartbeats, devices } from '../schema';

type DeviceHeartbeatInsert = typeof deviceHeartbeats.$inferInsert;

interface HeartbeatSeedRecord {
  deviceCode: string;
  status: DeviceHeartbeatInsert['status'];
  ipAddress: string | null;
  firmwareVersion: string | null;
  uptimeSeconds: number;
  metadata: Record<string, unknown>;
}

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

async function heartbeatExists(deviceId: string): Promise<boolean> {
  const [heartbeat] = await db
    .select({
      id: deviceHeartbeats.id,
    })
    .from(deviceHeartbeats)
    .where(eq(deviceHeartbeats.deviceId, deviceId))
    .limit(1);

  return Boolean(heartbeat);
}

async function insertHeartbeat(record: HeartbeatSeedRecord): Promise<void> {
  const deviceId = await getDeviceId(record.deviceCode);

  if (await heartbeatExists(deviceId)) {
    return;
  }

  await db.insert(deviceHeartbeats).values({
    deviceId,
    status: record.status,
    heartbeatAt: new Date(),
    ipAddress: record.ipAddress,
    firmwareVersion: record.firmwareVersion,
    uptimeSeconds: record.uptimeSeconds,
    metadata: {
      ...record.metadata,
      source: 'database_seed',
      seededDeviceCode: record.deviceCode,
    },
  });
}

export async function seedDeviceHeartbeats(): Promise<void> {
  console.log('Seeding device heartbeats...');

  const heartbeatRecords: HeartbeatSeedRecord[] = [
    /*
    |--------------------------------------------------------------------------
    | MCC HEADQUARTERS
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-JETSON-HQ-001',
      status: 'online',
      ipAddress: '192.168.10.20',
      firmwareVersion: 'JetPack 6.x',
      uptimeSeconds: 172800,
      metadata: {
        deviceRole: 'ai_processing_node',
        connectionType: 'ethernet',
        operatingSystem: 'Ubuntu',
        services: ['video_ingestion', 'ai_inference', 'alert_processing'],
      },
    },
    {
      deviceCode: 'DEV-SERVER-HQ-001',
      status: 'online',
      ipAddress: '192.168.10.10',
      firmwareVersion: 'Ubuntu Server',
      uptimeSeconds: 604800,
      metadata: {
        deviceRole: 'application_server',
        connectionType: 'ethernet',
        services: ['api', 'database', 'storage'],
      },
    },
    {
      deviceCode: 'DEV-SWITCH-HQ-001',
      status: 'online',
      ipAddress: '192.168.10.2',
      firmwareVersion: '1.0.0',
      uptimeSeconds: 1209600,
      metadata: {
        deviceRole: 'network_switch',
        connectionType: 'ethernet',
        managed: true,
      },
    },
    {
      deviceCode: 'DEV-UPS-HQ-001',
      status: 'online',
      ipAddress: null,
      firmwareVersion: '1.0.0',
      uptimeSeconds: 1209600,
      metadata: {
        deviceRole: 'backup_power',
        communicationType: 'local_monitoring',
        batteryStatus: 'normal',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | HQ NANOSTATION RECEIVERS
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-NANO-HQ-001',
      status: 'online',
      ipAddress: '192.168.10.101',
      firmwareVersion: 'airOS 6.x',
      uptimeSeconds: 432000,
      metadata: {
        deviceRole: 'wireless_receiver',
        connectionType: 'wireless_bridge',
        linkedFieldDevice: 'DEV-NANO-FIELD-001',
        frequencyBand: '5GHz',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-002',
      status: 'online',
      ipAddress: '192.168.10.102',
      firmwareVersion: 'airOS 6.x',
      uptimeSeconds: 432000,
      metadata: {
        deviceRole: 'wireless_receiver',
        connectionType: 'wireless_bridge',
        linkedFieldDevice: 'DEV-NANO-FIELD-002',
        frequencyBand: '5GHz',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-003',
      status: 'online',
      ipAddress: '192.168.10.103',
      firmwareVersion: 'airOS 6.x',
      uptimeSeconds: 432000,
      metadata: {
        deviceRole: 'wireless_receiver',
        connectionType: 'wireless_bridge',
        deploymentPurpose: 'future_field_site',
        frequencyBand: '5GHz',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-004',
      status: 'online',
      ipAddress: '192.168.10.104',
      firmwareVersion: 'airOS 6.x',
      uptimeSeconds: 432000,
      metadata: {
        deviceRole: 'wireless_receiver',
        connectionType: 'wireless_bridge',
        deploymentPurpose: 'future_field_site',
        frequencyBand: '5GHz',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 001
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-CAMERA-FIELD-001',
      status: 'online',
      ipAddress: '192.168.20.10',
      firmwareVersion: 'V380 SC31 Firmware',
      uptimeSeconds: 86400,
      metadata: {
        deviceRole: 'surveillance_camera',
        connectionType: 'ethernet',
        cameraModel: 'V380 SC31 PTZ',
        poweredBy: 'PWR-FIELD-001',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-001',
      status: 'online',
      ipAddress: '192.168.20.2',
      firmwareVersion: 'airOS 6.x',
      uptimeSeconds: 86400,
      metadata: {
        deviceRole: 'wireless_transmitter',
        connectionType: 'wireless_bridge',
        linkedHqDevice: 'DEV-NANO-HQ-001',
        poweredBy: 'PWR-FIELD-001',
        frequencyBand: '5GHz',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 002
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-CAMERA-FIELD-002',
      status: 'online',
      ipAddress: '192.168.30.10',
      firmwareVersion: 'V380 SC31 Firmware',
      uptimeSeconds: 43200,
      metadata: {
        deviceRole: 'surveillance_camera',
        connectionType: 'ethernet',
        cameraModel: 'V380 SC31 PTZ',
        poweredBy: 'PWR-FIELD-002',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-002',
      status: 'online',
      ipAddress: '192.168.30.2',
      firmwareVersion: 'airOS 6.x',
      uptimeSeconds: 43200,
      metadata: {
        deviceRole: 'wireless_transmitter',
        connectionType: 'wireless_bridge',
        linkedHqDevice: 'DEV-NANO-HQ-002',
        poweredBy: 'PWR-FIELD-002',
        frequencyBand: '5GHz',
      },
    },
  ];

  for (const heartbeatRecord of heartbeatRecords) {
    await insertHeartbeat(heartbeatRecord);
  }

  console.log('Device heartbeats seeded.');
}
