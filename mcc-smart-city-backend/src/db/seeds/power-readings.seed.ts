import { and, eq } from 'drizzle-orm';

import { db } from '../index';
import { powerReadings, powerSystems } from '../schema';

type PowerReadingInsert = typeof powerReadings.$inferInsert;

interface PowerReadingSeedRecord {
  powerSystemCode: string;

  solarVoltage: string | null;
  solarCurrentAmps: string | null;
  solarPowerWatts: string | null;

  batteryVoltage: string | null;
  batteryCurrentAmps: string | null;
  batteryStateOfChargePercent: string | null;
  batteryTemperatureCelsius: string | null;

  loadVoltage: string | null;
  loadCurrentAmps: string | null;
  loadPowerWatts: string | null;

  estimatedRuntimeMinutes: number | null;
  chargingState: string | null;
  controllerTemperatureCelsius: string | null;

  metadata?: Record<string, unknown>;
}

/*
|--------------------------------------------------------------------------
| Deterministic seed timestamp
|--------------------------------------------------------------------------
|
| The fixed timestamp prevents duplicate baseline readings when the database
| seed command is run multiple times.
|
*/

const SEED_RECORDED_AT = new Date('2026-07-20T08:00:00.000Z');

async function getPowerSystemId(powerSystemCode: string): Promise<string> {
  const [powerSystem] = await db
    .select({
      id: powerSystems.id,
    })
    .from(powerSystems)
    .where(eq(powerSystems.powerSystemCode, powerSystemCode))
    .limit(1);

  if (!powerSystem) {
    throw new Error(
      `Power system "${powerSystemCode}" was not found. Run the power-systems seed first.`,
    );
  }

  return powerSystem.id;
}

async function readingExists(
  powerSystemId: string,
  recordedAt: Date,
): Promise<boolean> {
  const [existingReading] = await db
    .select({
      id: powerReadings.id,
    })
    .from(powerReadings)
    .where(
      and(
        eq(powerReadings.powerSystemId, powerSystemId),
        eq(powerReadings.recordedAt, recordedAt),
      ),
    )
    .limit(1);

  return Boolean(existingReading);
}

async function insertPowerReading(
  record: PowerReadingSeedRecord,
): Promise<void> {
  const powerSystemId = await getPowerSystemId(record.powerSystemCode);

  const alreadyExists = await readingExists(powerSystemId, SEED_RECORDED_AT);

  if (alreadyExists) {
    return;
  }

  const reading: PowerReadingInsert = {
    powerSystemId,

    solarVoltage: record.solarVoltage,
    solarCurrentAmps: record.solarCurrentAmps,
    solarPowerWatts: record.solarPowerWatts,

    batteryVoltage: record.batteryVoltage,
    batteryCurrentAmps: record.batteryCurrentAmps,
    batteryStateOfChargePercent: record.batteryStateOfChargePercent,
    batteryTemperatureCelsius: record.batteryTemperatureCelsius,

    loadVoltage: record.loadVoltage,
    loadCurrentAmps: record.loadCurrentAmps,
    loadPowerWatts: record.loadPowerWatts,

    estimatedRuntimeMinutes: record.estimatedRuntimeMinutes,
    chargingState: record.chargingState,
    controllerTemperatureCelsius: record.controllerTemperatureCelsius,

    recordedAt: SEED_RECORDED_AT,

    metadata: {
      source: 'database_seed',
      baselineMeasurement: true,
      seededPowerSystemCode: record.powerSystemCode,
      ...record.metadata,
    },
  };

  await db.insert(powerReadings).values(reading);
}

export async function seedPowerReadings(): Promise<void> {
  console.log('Seeding power readings...');

  const readingRecords: PowerReadingSeedRecord[] = [
    /*
    |--------------------------------------------------------------------------
    | MCC HEADQUARTERS UPS
    |--------------------------------------------------------------------------
    */

    {
      powerSystemCode: 'PWR-HQ-001',

      solarVoltage: null,
      solarCurrentAmps: null,
      solarPowerWatts: null,

      batteryVoltage: '27.200',
      batteryCurrentAmps: '-2.400',
      batteryStateOfChargePercent: '96.00',
      batteryTemperatureCelsius: '28.40',

      loadVoltage: '230.100',
      loadCurrentAmps: '1.850',
      loadPowerWatts: '425.700',

      estimatedRuntimeMinutes: 57,
      chargingState: 'float_charging',
      controllerTemperatureCelsius: '31.20',

      metadata: {
        category: 'ups',
        locationCode: 'MCC-HQ',
        powerSource: 'mains',
        utilityAvailable: true,
        operatingMode: 'online',
        protectedEquipment: [
          'DEV-SERVER-HQ-001',
          'DEV-JETSON-HQ-001',
          'DEV-SWITCH-HQ-001',
        ],
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 001 SOLAR SYSTEM
    |--------------------------------------------------------------------------
    */

    {
      powerSystemCode: 'PWR-FIELD-001',

      solarVoltage: '18.620',
      solarCurrentAmps: '2.310',
      solarPowerWatts: '43.012',

      batteryVoltage: '13.420',
      batteryCurrentAmps: '1.080',
      batteryStateOfChargePercent: '84.00',
      batteryTemperatureCelsius: '27.80',

      loadVoltage: '12.310',
      loadCurrentAmps: '1.940',
      loadPowerWatts: '23.881',

      estimatedRuntimeMinutes: 610,
      chargingState: 'bulk_charging',
      controllerTemperatureCelsius: '32.60',

      metadata: {
        category: 'solar_battery',
        locationCode: 'FIELD-SITE-001',
        batteryChemistry: 'gel_lead_acid',
        batteryModel: 'DGM-BA28AH',
        batteryCapacityAmpHours: 28,
        solarPanelCapacityWatts: 50,
        connectedLoads: ['DEV-CAMERA-FIELD-001', 'DEV-NANO-FIELD-001'],
        weatherCondition: 'clear',
        powerCondition: 'normal',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 002 SOLAR SYSTEM
    |--------------------------------------------------------------------------
    */

    {
      powerSystemCode: 'PWR-FIELD-002',

      solarVoltage: '17.940',
      solarCurrentAmps: '1.970',
      solarPowerWatts: '35.342',

      batteryVoltage: '12.880',
      batteryCurrentAmps: '0.720',
      batteryStateOfChargePercent: '71.00',
      batteryTemperatureCelsius: '28.30',

      loadVoltage: '12.180',
      loadCurrentAmps: '1.890',
      loadPowerWatts: '23.020',

      estimatedRuntimeMinutes: 495,
      chargingState: 'absorption_charging',
      controllerTemperatureCelsius: '33.10',

      metadata: {
        category: 'solar_battery',
        locationCode: 'FIELD-SITE-002',
        batteryChemistry: 'gel_lead_acid',
        batteryCapacityAmpHours: 28,
        solarPanelCapacityWatts: 50,
        connectedLoads: ['DEV-CAMERA-FIELD-002', 'DEV-NANO-FIELD-002'],
        weatherCondition: 'partly_cloudy',
        powerCondition: 'normal',
      },
    },
  ];

  for (const readingRecord of readingRecords) {
    await insertPowerReading(readingRecord);
  }

  console.log(
    `Power readings seeded: ${readingRecords.length} baseline records.`,
  );
}
