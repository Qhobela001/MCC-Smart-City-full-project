import { eq } from 'drizzle-orm';

import { db } from '../index';
import { assets, locations, powerSystems } from '../schema';

type PowerSystemInsert = typeof powerSystems.$inferInsert;

async function getLocationId(locationCode: string): Promise<string> {
  const [location] = await db
    .select({
      id: locations.id,
    })
    .from(locations)
    .where(eq(locations.locationCode, locationCode))
    .limit(1);

  if (!location) {
    throw new Error(
      `Location "${locationCode}" was not found. Run the locations seed first.`,
    );
  }

  return location.id;
}

async function getAssetId(assetCode: string): Promise<string> {
  const [asset] = await db
    .select({
      id: assets.id,
    })
    .from(assets)
    .where(eq(assets.assetCode, assetCode))
    .limit(1);

  if (!asset) {
    throw new Error(
      `Asset "${assetCode}" was not found. Run the assets seed first.`,
    );
  }

  return asset.id;
}

export async function seedPowerSystems(): Promise<void> {
  console.log('Seeding power systems...');

  const [
    hqLocationId,
    fieldSiteOneId,
    fieldSiteTwoId,
    hqUpsAssetId,
    fieldOneSolarAssetId,
    fieldOneBatteryAssetId,
    fieldOneControllerAssetId,
    fieldTwoSolarAssetId,
    fieldTwoBatteryAssetId,
    fieldTwoControllerAssetId,
  ] = await Promise.all([
    getLocationId('MCC-HQ'),
    getLocationId('FIELD-SITE-001'),
    getLocationId('FIELD-SITE-002'),
    getAssetId('AST-UPS-HQ-001'),
    getAssetId('AST-SOLAR-FIELD-001'),
    getAssetId('AST-BATTERY-FIELD-001'),
    getAssetId('AST-CONTROLLER-FIELD-001'),
    getAssetId('AST-SOLAR-FIELD-002'),
    getAssetId('AST-BATTERY-FIELD-002'),
    getAssetId('AST-CONTROLLER-FIELD-002'),
  ]);

  const powerSystemRecords: PowerSystemInsert[] = [
    {
      powerSystemCode: 'PWR-HQ-001',
      name: 'MCC Headquarters Backup Power System',
      type: 'solar_battery',
      status: 'planned',
      locationId: hqLocationId,
      upsAssetId: hqUpsAssetId,
      nominalSystemVoltage: '230.00',
      solarCapacityWatts: null,
      batteryCapacityAmpHours: null,
      maximumLoadWatts: null,
      lowBatteryThresholdPercent: '20.00',
      lastCheckedAt: null,
      metadata: {
        deploymentState: 'planned',
        role: 'backup_power',
        protectedEquipment: [
          'DEV-SERVER-HQ-001',
          'DEV-JETSON-HQ-001',
          'DEV-SWITCH-HQ-001',
        ],
        notes:
          'UPS capacity and runtime must be confirmed after the final server and network load are measured.',
      },
    },
    {
      powerSystemCode: 'PWR-FIELD-001',
      name: 'Field Site 1 Solar Power System',
      type: 'solar_battery',
      status: 'planned',
      locationId: fieldSiteOneId,
      solarPanelAssetId: fieldOneSolarAssetId,
      batteryAssetId: fieldOneBatteryAssetId,
      chargeControllerAssetId: fieldOneControllerAssetId,
      nominalSystemVoltage: '12.00',
      solarCapacityWatts: '50.00',
      batteryCapacityAmpHours: '28.00',
      maximumLoadWatts: '30.00',
      lowBatteryThresholdPercent: '20.00',
      lastCheckedAt: null,
      metadata: {
        deploymentState: 'testing',
        batteryChemistry: 'gel_lead_acid',
        batteryModel: 'DGM-BA28AH',
        estimatedStoredEnergyWh: 336,
        connectedLoads: [
          {
            deviceCode: 'DEV-CAMERA-FIELD-001',
            estimatedMaximumWatts: 24,
          },
          {
            deviceCode: 'DEV-NANO-FIELD-001',
            estimatedMaximumWatts: 6,
          },
        ],
        estimatedMaximumCombinedLoadWatts: 30,
        theoreticalRuntimeHoursAtMaximumLoad: 11.2,
        notes:
          'Theoretical runtime does not account for inverter, cable, controller, temperature or battery depth-of-discharge losses.',
      },
    },
    {
      powerSystemCode: 'PWR-FIELD-002',
      name: 'Field Site 2 Solar Power System',
      type: 'solar_battery',
      status: 'planned',
      locationId: fieldSiteTwoId,
      solarPanelAssetId: fieldTwoSolarAssetId,
      batteryAssetId: fieldTwoBatteryAssetId,
      chargeControllerAssetId: fieldTwoControllerAssetId,
      nominalSystemVoltage: '12.00',
      solarCapacityWatts: '50.00',
      batteryCapacityAmpHours: '28.00',
      maximumLoadWatts: '30.00',
      lowBatteryThresholdPercent: '20.00',
      lastCheckedAt: null,
      metadata: {
        deploymentState: 'planned',
        batteryChemistry: 'gel_lead_acid',
        estimatedStoredEnergyWh: 336,
        connectedLoads: [
          {
            deviceCode: 'DEV-CAMERA-FIELD-002',
            estimatedMaximumWatts: 24,
          },
          {
            deviceCode: 'DEV-NANO-FIELD-002',
            estimatedMaximumWatts: 6,
          },
        ],
        estimatedMaximumCombinedLoadWatts: 30,
        theoreticalRuntimeHoursAtMaximumLoad: 11.2,
        notes:
          'Final equipment ratings and battery capacity must be confirmed before deployment.',
      },
    },
  ];

  await db
    .insert(powerSystems)
    .values(powerSystemRecords)
    .onConflictDoNothing();

  console.log('Power systems seeded.');
}
