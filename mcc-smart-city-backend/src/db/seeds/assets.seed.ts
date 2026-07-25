import { eq } from 'drizzle-orm';

import { db } from '../index';
import { assets, locations } from '../schema';

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
      `Location "${locationCode}" was not found. Run the location seed first.`,
    );
  }

  return location.id;
}

export async function seedAssets(): Promise<void> {
  console.log('Seeding assets...');

  const hqLocationId = await getLocationId('MCC-HQ');
  const fieldSiteOneId = await getLocationId('FIELD-SITE-001');
  const fieldSiteTwoId = await getLocationId('FIELD-SITE-002');

  await db
    .insert(assets)
    .values([
      /*
      |--------------------------------------------------------------------------
      | MCC HEADQUARTERS
      |--------------------------------------------------------------------------
      */

      {
        assetCode: 'AST-JETSON-HQ-001',
        assetName: 'NVIDIA Jetson Orin Nano 8GB',
        assetType: 'jetson',
        status: 'planned',
        manufacturer: 'NVIDIA',
        model: 'Jetson Orin Nano 8GB',
        expectedLifeYears: 5,
        locationId: hqLocationId,
      },
      {
        assetCode: 'AST-NANO-HQ-001',
        assetName: 'HQ NanoStation Receiver 1',
        assetType: 'nanostation',
        status: 'planned',
        manufacturer: 'Ubiquiti',
        model: 'NanoStation Loco M5',
        expectedLifeYears: 5,
        locationId: hqLocationId,
      },
      {
        assetCode: 'AST-NANO-HQ-002',
        assetName: 'HQ NanoStation Receiver 2',
        assetType: 'nanostation',
        status: 'planned',
        manufacturer: 'Ubiquiti',
        model: 'NanoStation Loco M5',
        expectedLifeYears: 5,
        locationId: hqLocationId,
      },
      {
        assetCode: 'AST-NANO-HQ-003',
        assetName: 'HQ NanoStation Receiver 3',
        assetType: 'nanostation',
        status: 'planned',
        manufacturer: 'Ubiquiti',
        model: 'NanoStation Loco M5',
        expectedLifeYears: 5,
        locationId: hqLocationId,
      },
      {
        assetCode: 'AST-NANO-HQ-004',
        assetName: 'HQ NanoStation Receiver 4',
        assetType: 'nanostation',
        status: 'planned',
        manufacturer: 'Ubiquiti',
        model: 'NanoStation Loco M5',
        expectedLifeYears: 5,
        locationId: hqLocationId,
      },
      {
        assetCode: 'AST-SERVER-HQ-001',
        assetName: 'MCC Smart City Backend Server',
        assetType: 'server',
        status: 'planned',
        expectedLifeYears: 5,
        locationId: hqLocationId,
      },
      {
        assetCode: 'AST-SWITCH-HQ-001',
        assetName: 'MCC Smart City Managed Network Switch',
        assetType: 'network_switch',
        status: 'planned',
        expectedLifeYears: 5,
        locationId: hqLocationId,
      },
      {
        assetCode: 'AST-UPS-HQ-001',
        assetName: 'MCC Smart City Server UPS',
        assetType: 'ups',
        status: 'planned',
        expectedLifeYears: 4,
        locationId: hqLocationId,
      },

      /*
      |--------------------------------------------------------------------------
      | FIELD SITE 001
      |--------------------------------------------------------------------------
      */

      {
        assetCode: 'AST-CAMERA-FIELD-001',
        assetName: 'V380 SC31 PTZ Camera',
        assetType: 'camera',
        status: 'planned',
        manufacturer: 'V380',
        model: 'SC31 PTZ',
        expectedLifeYears: 4,
        locationId: fieldSiteOneId,
      },
      {
        assetCode: 'AST-NANO-FIELD-001',
        assetName: 'Field NanoStation Site 1',
        assetType: 'nanostation',
        status: 'planned',
        manufacturer: 'Ubiquiti',
        model: 'NanoStation Loco M5',
        expectedLifeYears: 5,
        locationId: fieldSiteOneId,
      },
      {
        assetCode: 'AST-POLE-FIELD-001',
        assetName: 'Camera Installation Pole Site 1',
        assetType: 'pole',
        status: 'planned',
        expectedLifeYears: 15,
        locationId: fieldSiteOneId,
      },
      {
        assetCode: 'AST-CABINET-FIELD-001',
        assetName: 'Weatherproof Equipment Cabinet Site 1',
        assetType: 'cabinet',
        status: 'planned',
        expectedLifeYears: 10,
        locationId: fieldSiteOneId,
      },
      {
        assetCode: 'AST-SOLAR-FIELD-001',
        assetName: '50 Watt Solar Panel Site 1',
        assetType: 'solar_panel',
        status: 'planned',
        model: '50W Solar Panel',
        expectedLifeYears: 15,
        locationId: fieldSiteOneId,
      },
      {
        assetCode: 'AST-BATTERY-FIELD-001',
        assetName: '12V 28Ah GEL Battery Site 1',
        assetType: 'battery',
        status: 'planned',
        manufacturer: 'DGM',
        model: 'DGM-BA28AH',
        expectedLifeYears: 3,
        locationId: fieldSiteOneId,
      },
      {
        assetCode: 'AST-CONTROLLER-FIELD-001',
        assetName: 'Solar Charge Controller Site 1',
        assetType: 'charge_controller',
        status: 'planned',
        model: '12/24V Solar Charge Controller',
        expectedLifeYears: 5,
        locationId: fieldSiteOneId,
      },

      /*
      |--------------------------------------------------------------------------
      | FIELD SITE 002
      |--------------------------------------------------------------------------
      */

      {
        assetCode: 'AST-CAMERA-FIELD-002',
        assetName: 'Planned Camera Site 2',
        assetType: 'camera',
        status: 'planned',
        expectedLifeYears: 4,
        locationId: fieldSiteTwoId,
      },
      {
        assetCode: 'AST-NANO-FIELD-002',
        assetName: 'Field NanoStation Site 2',
        assetType: 'nanostation',
        status: 'planned',
        manufacturer: 'Ubiquiti',
        model: 'NanoStation Loco M5',
        expectedLifeYears: 5,
        locationId: fieldSiteTwoId,
      },
      {
        assetCode: 'AST-POLE-FIELD-002',
        assetName: 'Camera Installation Pole Site 2',
        assetType: 'pole',
        status: 'planned',
        expectedLifeYears: 15,
        locationId: fieldSiteTwoId,
      },
      {
        assetCode: 'AST-CABINET-FIELD-002',
        assetName: 'Weatherproof Equipment Cabinet Site 2',
        assetType: 'cabinet',
        status: 'planned',
        expectedLifeYears: 10,
        locationId: fieldSiteTwoId,
      },
      {
        assetCode: 'AST-SOLAR-FIELD-002',
        assetName: 'Planned Solar Panel Site 2',
        assetType: 'solar_panel',
        status: 'planned',
        expectedLifeYears: 15,
        locationId: fieldSiteTwoId,
      },
      {
        assetCode: 'AST-BATTERY-FIELD-002',
        assetName: 'Planned Battery Site 2',
        assetType: 'battery',
        status: 'planned',
        expectedLifeYears: 3,
        locationId: fieldSiteTwoId,
      },
      {
        assetCode: 'AST-CONTROLLER-FIELD-002',
        assetName: 'Planned Charge Controller Site 2',
        assetType: 'charge_controller',
        status: 'planned',
        expectedLifeYears: 5,
        locationId: fieldSiteTwoId,
      },
    ])
    .onConflictDoNothing();

  console.log('Assets seeded.');
}
