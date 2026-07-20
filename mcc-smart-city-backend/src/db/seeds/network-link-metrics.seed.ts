import { and, eq } from 'drizzle-orm';

import { db } from '../index';
import { networkLinkMetrics, networkLinks } from '../schema';

type NetworkLinkMetricInsert = typeof networkLinkMetrics.$inferInsert;

interface NetworkLinkMetricSeedRecord {
  networkLinkCode: string;
  signalStrengthDbm: string | null;
  noiseFloorDbm: string | null;
  signalToNoiseRatioDb: string | null;
  transmitCapacityMbps: string | null;
  receiveCapacityMbps: string | null;
  transmitThroughputMbps: string | null;
  receiveThroughputMbps: string | null;
  latencyMs: string | null;
  packetLossPercent: string | null;
  airmaxQualityPercent: string | null;
  airmaxCapacityPercent: string | null;
  connectionCount: number | null;
  metadata?: Record<string, unknown>;
}

/*
|--------------------------------------------------------------------------
| Deterministic seed timestamp
|--------------------------------------------------------------------------
|
| The fixed timestamp prevents duplicate baseline readings when the seed
| command is run more than once.
|
*/

const SEED_RECORDED_AT = new Date('2026-07-20T08:00:00.000Z');

async function getNetworkLinkId(networkLinkCode: string): Promise<string> {
  const [networkLink] = await db
    .select({
      id: networkLinks.id,
    })
    .from(networkLinks)
    .where(eq(networkLinks.linkCode, networkLinkCode))
    .limit(1);

  if (!networkLink) {
    throw new Error(
      `Network link "${networkLinkCode}" was not found. Run the network-links seed first.`,
    );
  }

  return networkLink.id;
}

async function metricExists(
  networkLinkId: string,
  recordedAt: Date,
): Promise<boolean> {
  const [existingMetric] = await db
    .select({
      id: networkLinkMetrics.id,
    })
    .from(networkLinkMetrics)
    .where(
      and(
        eq(networkLinkMetrics.networkLinkId, networkLinkId),
        eq(networkLinkMetrics.recordedAt, recordedAt),
      ),
    )
    .limit(1);

  return Boolean(existingMetric);
}

async function insertNetworkLinkMetric(
  record: NetworkLinkMetricSeedRecord,
): Promise<void> {
  const networkLinkId = await getNetworkLinkId(record.networkLinkCode);

  const alreadyExists = await metricExists(networkLinkId, SEED_RECORDED_AT);

  if (alreadyExists) {
    return;
  }

  const metric: NetworkLinkMetricInsert = {
    networkLinkId,
    signalStrengthDbm: record.signalStrengthDbm,
    noiseFloorDbm: record.noiseFloorDbm,
    signalToNoiseRatioDb: record.signalToNoiseRatioDb,
    transmitCapacityMbps: record.transmitCapacityMbps,
    receiveCapacityMbps: record.receiveCapacityMbps,
    transmitThroughputMbps: record.transmitThroughputMbps,
    receiveThroughputMbps: record.receiveThroughputMbps,
    latencyMs: record.latencyMs,
    packetLossPercent: record.packetLossPercent,
    airmaxQualityPercent: record.airmaxQualityPercent,
    airmaxCapacityPercent: record.airmaxCapacityPercent,
    connectionCount: record.connectionCount,
    recordedAt: SEED_RECORDED_AT,
    metadata: {
      source: 'database_seed',
      baselineMeasurement: true,
      seededNetworkLinkCode: record.networkLinkCode,
      ...record.metadata,
    },
  };

  await db.insert(networkLinkMetrics).values(metric);
}

export async function seedNetworkLinkMetrics(): Promise<void> {
  console.log('Seeding network link metrics...');

  const metricRecords: NetworkLinkMetricSeedRecord[] = [
    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 001 WIRELESS LINK
    |--------------------------------------------------------------------------
    */

    {
      networkLinkCode: 'LINK-WIRELESS-FIELD-001-HQ-001',
      signalStrengthDbm: '-58.00',
      noiseFloorDbm: '-94.00',
      signalToNoiseRatioDb: '36.00',
      transmitCapacityMbps: '86.70',
      receiveCapacityMbps: '78.40',
      transmitThroughputMbps: '18.60',
      receiveThroughputMbps: '4.20',
      latencyMs: '2.450',
      packetLossPercent: '0.23',
      airmaxQualityPercent: '93.50',
      airmaxCapacityPercent: '89.20',
      connectionCount: 1,
      metadata: {
        category: 'wireless',
        technology: 'airMAX',
        frequencyBand: '5GHz',
        sourceDeviceCode: 'DEV-NANO-FIELD-001',
        destinationDeviceCode: 'DEV-NANO-HQ-001',
        fieldSiteCode: 'FIELD-SITE-001',
        linkCondition: 'good',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 002 WIRELESS LINK
    |--------------------------------------------------------------------------
    */

    {
      networkLinkCode: 'LINK-WIRELESS-FIELD-001-HQ-001',
      signalStrengthDbm: '-62.00',
      noiseFloorDbm: '-95.00',
      signalToNoiseRatioDb: '33.00',
      transmitCapacityMbps: '72.60',
      receiveCapacityMbps: '69.10',
      transmitThroughputMbps: '17.80',
      receiveThroughputMbps: '3.90',
      latencyMs: '3.180',
      packetLossPercent: '0.41',
      airmaxQualityPercent: '89.80',
      airmaxCapacityPercent: '84.60',
      connectionCount: 1,
      metadata: {
        category: 'wireless',
        technology: 'airMAX',
        frequencyBand: '5GHz',
        sourceDeviceCode: 'DEV-NANO-FIELD-002',
        destinationDeviceCode: 'DEV-NANO-HQ-002',
        fieldSiteCode: 'FIELD-SITE-002',
        linkCondition: 'acceptable',
      },
    },
  ];

  for (const metricRecord of metricRecords) {
    await insertNetworkLinkMetric(metricRecord);
  }

  console.log(
    `Network link metrics seeded: ${metricRecords.length} baseline records.`,
  );
}
