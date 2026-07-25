import { and, eq } from 'drizzle-orm';

import { db } from '../index';
import { deviceMetrics, devices } from '../schema';

type DeviceMetricInsert = typeof deviceMetrics.$inferInsert;

interface DeviceMetricSeedRecord {
  deviceCode: string;
  metricName: string;
  metricValue: string;
  metricUnit: string | null;
  metadata?: Record<string, unknown>;
}

/*
|--------------------------------------------------------------------------
| Deterministic seed timestamp
|--------------------------------------------------------------------------
|
| A fixed timestamp makes the seed idempotent. Without a unique constraint
| on device_metrics, using new Date() on every run would create duplicate
| time-series records.
|
*/

const SEED_RECORDED_AT = new Date('2026-07-20T08:00:00.000Z');

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

async function metricExists(
  deviceId: string,
  metricName: string,
): Promise<boolean> {
  const [existingMetric] = await db
    .select({
      id: deviceMetrics.id,
    })
    .from(deviceMetrics)
    .where(
      and(
        eq(deviceMetrics.deviceId, deviceId),
        eq(deviceMetrics.metricName, metricName),
        eq(deviceMetrics.recordedAt, SEED_RECORDED_AT),
      ),
    )
    .limit(1);

  return Boolean(existingMetric);
}

async function insertMetric(record: DeviceMetricSeedRecord): Promise<void> {
  const deviceId = await getDeviceId(record.deviceCode);

  const alreadyExists = await metricExists(deviceId, record.metricName);

  if (alreadyExists) {
    return;
  }

  const metric: DeviceMetricInsert = {
    deviceId,
    metricName: record.metricName,
    metricValue: record.metricValue,
    metricUnit: record.metricUnit,
    recordedAt: SEED_RECORDED_AT,
    metadata: {
      source: 'database_seed',
      seededDeviceCode: record.deviceCode,
      baselineMeasurement: true,
      ...record.metadata,
    },
  };

  await db.insert(deviceMetrics).values(metric);
}

export async function seedDeviceMetrics(): Promise<void> {
  console.log('Seeding device metrics...');

  const metricRecords: DeviceMetricSeedRecord[] = [
    /*
    |--------------------------------------------------------------------------
    | JETSON ORIN NANO
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-JETSON-HQ-001',
      metricName: 'cpu_usage_percent',
      metricValue: '34.500000',
      metricUnit: 'percent',
      metadata: {
        category: 'system',
        component: 'cpu',
      },
    },
    {
      deviceCode: 'DEV-JETSON-HQ-001',
      metricName: 'gpu_usage_percent',
      metricValue: '48.200000',
      metricUnit: 'percent',
      metadata: {
        category: 'system',
        component: 'gpu',
      },
    },
    {
      deviceCode: 'DEV-JETSON-HQ-001',
      metricName: 'memory_usage_percent',
      metricValue: '41.800000',
      metricUnit: 'percent',
      metadata: {
        category: 'system',
        component: 'memory',
      },
    },
    {
      deviceCode: 'DEV-JETSON-HQ-001',
      metricName: 'temperature_celsius',
      metricValue: '46.300000',
      metricUnit: 'celsius',
      metadata: {
        category: 'environment',
        sensor: 'soc',
      },
    },
    {
      deviceCode: 'DEV-JETSON-HQ-001',
      metricName: 'power_consumption_watts',
      metricValue: '11.700000',
      metricUnit: 'watts',
      metadata: {
        category: 'power',
      },
    },
    {
      deviceCode: 'DEV-JETSON-HQ-001',
      metricName: 'ai_inference_fps',
      metricValue: '18.500000',
      metricUnit: 'fps',
      metadata: {
        category: 'ai',
        workload: 'video_analytics',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | HQ APPLICATION SERVER
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-SERVER-HQ-001',
      metricName: 'cpu_usage_percent',
      metricValue: '27.400000',
      metricUnit: 'percent',
      metadata: {
        category: 'system',
        component: 'cpu',
      },
    },
    {
      deviceCode: 'DEV-SERVER-HQ-001',
      metricName: 'memory_usage_percent',
      metricValue: '52.600000',
      metricUnit: 'percent',
      metadata: {
        category: 'system',
        component: 'memory',
      },
    },
    {
      deviceCode: 'DEV-SERVER-HQ-001',
      metricName: 'disk_usage_percent',
      metricValue: '38.900000',
      metricUnit: 'percent',
      metadata: {
        category: 'storage',
        mountPoint: '/',
      },
    },
    {
      deviceCode: 'DEV-SERVER-HQ-001',
      metricName: 'network_receive_mbps',
      metricValue: '24.700000',
      metricUnit: 'mbps',
      metadata: {
        category: 'network',
        interface: 'ethernet',
      },
    },
    {
      deviceCode: 'DEV-SERVER-HQ-001',
      metricName: 'network_transmit_mbps',
      metricValue: '8.300000',
      metricUnit: 'mbps',
      metadata: {
        category: 'network',
        interface: 'ethernet',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | HQ MANAGED SWITCH
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-SWITCH-HQ-001',
      metricName: 'cpu_usage_percent',
      metricValue: '16.200000',
      metricUnit: 'percent',
      metadata: {
        category: 'system',
      },
    },
    {
      deviceCode: 'DEV-SWITCH-HQ-001',
      metricName: 'active_ports_count',
      metricValue: '8.000000',
      metricUnit: 'ports',
      metadata: {
        category: 'network',
      },
    },
    {
      deviceCode: 'DEV-SWITCH-HQ-001',
      metricName: 'network_throughput_mbps',
      metricValue: '63.400000',
      metricUnit: 'mbps',
      metadata: {
        category: 'network',
      },
    },
    {
      deviceCode: 'DEV-SWITCH-HQ-001',
      metricName: 'packet_loss_percent',
      metricValue: '0.080000',
      metricUnit: 'percent',
      metadata: {
        category: 'network',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | HQ UPS
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-UPS-HQ-001',
      metricName: 'input_voltage_volts',
      metricValue: '229.800000',
      metricUnit: 'volts',
      metadata: {
        category: 'power',
      },
    },
    {
      deviceCode: 'DEV-UPS-HQ-001',
      metricName: 'output_voltage_volts',
      metricValue: '230.100000',
      metricUnit: 'volts',
      metadata: {
        category: 'power',
      },
    },
    {
      deviceCode: 'DEV-UPS-HQ-001',
      metricName: 'battery_charge_percent',
      metricValue: '96.000000',
      metricUnit: 'percent',
      metadata: {
        category: 'battery',
      },
    },
    {
      deviceCode: 'DEV-UPS-HQ-001',
      metricName: 'load_percent',
      metricValue: '42.000000',
      metricUnit: 'percent',
      metadata: {
        category: 'power',
      },
    },
    {
      deviceCode: 'DEV-UPS-HQ-001',
      metricName: 'estimated_runtime_minutes',
      metricValue: '57.000000',
      metricUnit: 'minutes',
      metadata: {
        category: 'battery',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | HQ NANOSTATION 001
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-NANO-HQ-001',
      metricName: 'signal_strength_dbm',
      metricValue: '-57.000000',
      metricUnit: 'dbm',
      metadata: {
        category: 'wireless',
        peerDeviceCode: 'DEV-NANO-FIELD-001',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-001',
      metricName: 'noise_floor_dbm',
      metricValue: '-94.000000',
      metricUnit: 'dbm',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-001',
      metricName: 'tx_rate_mbps',
      metricValue: '86.700000',
      metricUnit: 'mbps',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-001',
      metricName: 'rx_rate_mbps',
      metricValue: '78.400000',
      metricUnit: 'mbps',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-001',
      metricName: 'ccq_percent',
      metricValue: '93.500000',
      metricUnit: 'percent',
      metadata: {
        category: 'wireless',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | HQ NANOSTATION 002
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-NANO-HQ-002',
      metricName: 'signal_strength_dbm',
      metricValue: '-61.000000',
      metricUnit: 'dbm',
      metadata: {
        category: 'wireless',
        peerDeviceCode: 'DEV-NANO-FIELD-002',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-002',
      metricName: 'noise_floor_dbm',
      metricValue: '-95.000000',
      metricUnit: 'dbm',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-002',
      metricName: 'tx_rate_mbps',
      metricValue: '72.600000',
      metricUnit: 'mbps',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-002',
      metricName: 'rx_rate_mbps',
      metricValue: '69.100000',
      metricUnit: 'mbps',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-002',
      metricName: 'ccq_percent',
      metricValue: '89.800000',
      metricUnit: 'percent',
      metadata: {
        category: 'wireless',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | HQ NANOSTATIONS RESERVED FOR FUTURE SITES
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-NANO-HQ-003',
      metricName: 'cpu_usage_percent',
      metricValue: '8.400000',
      metricUnit: 'percent',
      metadata: {
        category: 'system',
        deploymentState: 'standby',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-003',
      metricName: 'temperature_celsius',
      metricValue: '37.200000',
      metricUnit: 'celsius',
      metadata: {
        category: 'environment',
        deploymentState: 'standby',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-004',
      metricName: 'cpu_usage_percent',
      metricValue: '7.900000',
      metricUnit: 'percent',
      metadata: {
        category: 'system',
        deploymentState: 'standby',
      },
    },
    {
      deviceCode: 'DEV-NANO-HQ-004',
      metricName: 'temperature_celsius',
      metricValue: '36.800000',
      metricUnit: 'celsius',
      metadata: {
        category: 'environment',
        deploymentState: 'standby',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD CAMERA 001
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-CAMERA-FIELD-001',
      metricName: 'stream_bitrate_kbps',
      metricValue: '3860.000000',
      metricUnit: 'kbps',
      metadata: {
        category: 'video',
        streamPurpose: 'primary',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-001',
      metricName: 'stream_fps',
      metricValue: '15.000000',
      metricUnit: 'fps',
      metadata: {
        category: 'video',
        streamPurpose: 'primary',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-001',
      metricName: 'temperature_celsius',
      metricValue: '41.700000',
      metricUnit: 'celsius',
      metadata: {
        category: 'environment',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-001',
      metricName: 'packet_loss_percent',
      metricValue: '0.230000',
      metricUnit: 'percent',
      metadata: {
        category: 'network',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD NANOSTATION 001
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-NANO-FIELD-001',
      metricName: 'signal_strength_dbm',
      metricValue: '-58.000000',
      metricUnit: 'dbm',
      metadata: {
        category: 'wireless',
        peerDeviceCode: 'DEV-NANO-HQ-001',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-001',
      metricName: 'noise_floor_dbm',
      metricValue: '-94.000000',
      metricUnit: 'dbm',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-001',
      metricName: 'tx_rate_mbps',
      metricValue: '78.400000',
      metricUnit: 'mbps',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-001',
      metricName: 'ccq_percent',
      metricValue: '92.700000',
      metricUnit: 'percent',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-001',
      metricName: 'input_voltage_volts',
      metricValue: '12.310000',
      metricUnit: 'volts',
      metadata: {
        category: 'power',
        powerSystemCode: 'PWR-FIELD-001',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD CAMERA 002
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-CAMERA-FIELD-002',
      metricName: 'stream_bitrate_kbps',
      metricValue: '3720.000000',
      metricUnit: 'kbps',
      metadata: {
        category: 'video',
        streamPurpose: 'primary',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-002',
      metricName: 'stream_fps',
      metricValue: '15.000000',
      metricUnit: 'fps',
      metadata: {
        category: 'video',
        streamPurpose: 'primary',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-002',
      metricName: 'temperature_celsius',
      metricValue: '40.900000',
      metricUnit: 'celsius',
      metadata: {
        category: 'environment',
      },
    },
    {
      deviceCode: 'DEV-CAMERA-FIELD-002',
      metricName: 'packet_loss_percent',
      metricValue: '0.410000',
      metricUnit: 'percent',
      metadata: {
        category: 'network',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD NANOSTATION 002
    |--------------------------------------------------------------------------
    */

    {
      deviceCode: 'DEV-NANO-FIELD-002',
      metricName: 'signal_strength_dbm',
      metricValue: '-62.000000',
      metricUnit: 'dbm',
      metadata: {
        category: 'wireless',
        peerDeviceCode: 'DEV-NANO-HQ-002',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-002',
      metricName: 'noise_floor_dbm',
      metricValue: '-95.000000',
      metricUnit: 'dbm',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-002',
      metricName: 'tx_rate_mbps',
      metricValue: '69.100000',
      metricUnit: 'mbps',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-002',
      metricName: 'ccq_percent',
      metricValue: '88.900000',
      metricUnit: 'percent',
      metadata: {
        category: 'wireless',
      },
    },
    {
      deviceCode: 'DEV-NANO-FIELD-002',
      metricName: 'input_voltage_volts',
      metricValue: '12.180000',
      metricUnit: 'volts',
      metadata: {
        category: 'power',
        powerSystemCode: 'PWR-FIELD-002',
      },
    },
  ];

  for (const metricRecord of metricRecords) {
    await insertMetric(metricRecord);
  }

  console.log(
    `Device metrics seeded: ${metricRecords.length} baseline records.`,
  );
}
