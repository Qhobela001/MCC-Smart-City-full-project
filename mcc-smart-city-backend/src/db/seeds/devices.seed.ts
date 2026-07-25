import { eq } from 'drizzle-orm';

import { db } from '../index';
import { assets, devices, locations } from '../schema';

type DeviceInsert = typeof devices.$inferInsert;

async function getAsset(assetCode: string): Promise<{
  id: string;
  locationId: string | null;
  assetName: string;
}> {
  const [asset] = await db
    .select({
      id: assets.id,
      locationId: assets.locationId,
      assetName: assets.assetName,
    })
    .from(assets)
    .where(eq(assets.assetCode, assetCode))
    .limit(1);

  if (!asset) {
    throw new Error(
      `Asset "${assetCode}" was not found. Run the assets seed first.`,
    );
  }

  return asset;
}

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

export async function seedDevices(): Promise<void> {
  console.log('Seeding devices...');

  const hqLocationId = await getLocationId('MCC-HQ');
  const fieldSiteOneId = await getLocationId('FIELD-SITE-001');
  const fieldSiteTwoId = await getLocationId('FIELD-SITE-002');

  const [
    jetsonAsset,
    hqNanoOneAsset,
    hqNanoTwoAsset,
    hqNanoThreeAsset,
    hqNanoFourAsset,
    serverAsset,
    switchAsset,
    upsAsset,
    cameraOneAsset,
    fieldNanoOneAsset,
    cameraTwoAsset,
    fieldNanoTwoAsset,
  ] = await Promise.all([
    getAsset('AST-JETSON-HQ-001'),
    getAsset('AST-NANO-HQ-001'),
    getAsset('AST-NANO-HQ-002'),
    getAsset('AST-NANO-HQ-003'),
    getAsset('AST-NANO-HQ-004'),
    getAsset('AST-SERVER-HQ-001'),
    getAsset('AST-SWITCH-HQ-001'),
    getAsset('AST-UPS-HQ-001'),
    getAsset('AST-CAMERA-FIELD-001'),
    getAsset('AST-NANO-FIELD-001'),
    getAsset('AST-CAMERA-FIELD-002'),
    getAsset('AST-NANO-FIELD-002'),
  ]);

  const deviceRecords: DeviceInsert[] = [
    /*
    |--------------------------------------------------------------------------
    | MCC HEADQUARTERS
    |--------------------------------------------------------------------------
    */

    {
      assetId: jetsonAsset.id,
      deviceCode: 'DEV-JETSON-HQ-001',
      name: 'MCC AI Processing Node 1',
      type: 'jetson',
      status: 'offline',
      manufacturer: 'NVIDIA',
      model: 'Jetson Orin Nano 8GB',
      ipAddress: '192.168.10.20',
      locationId: hqLocationId,
      metadata: {
        role: 'ai_processing',
        environment: 'production',
        deploymentState: 'planned',
        workloads: ['video_inference', 'incident_detection'],
        accelerator: 'NVIDIA Ampere GPU',
      },
    },
    {
      assetId: hqNanoOneAsset.id,
      deviceCode: 'DEV-NANO-HQ-001',
      name: 'HQ NanoStation Receiver 1',
      type: 'nanostation',
      status: 'offline',
      manufacturer: 'Ubiquiti',
      model: 'NanoStation Loco M5',
      ipAddress: '192.168.10.101',
      locationId: hqLocationId,
      metadata: {
        role: 'access_point',
        deploymentState: 'planned',
        frequencyBand: '5GHz',
        wirelessMode: 'bridge',
        assignedSector: 1,
      },
    },
    {
      assetId: hqNanoTwoAsset.id,
      deviceCode: 'DEV-NANO-HQ-002',
      name: 'HQ NanoStation Receiver 2',
      type: 'nanostation',
      status: 'offline',
      manufacturer: 'Ubiquiti',
      model: 'NanoStation Loco M5',
      ipAddress: '192.168.10.102',
      locationId: hqLocationId,
      metadata: {
        role: 'access_point',
        deploymentState: 'planned',
        frequencyBand: '5GHz',
        wirelessMode: 'bridge',
        assignedSector: 2,
      },
    },
    {
      assetId: hqNanoThreeAsset.id,
      deviceCode: 'DEV-NANO-HQ-003',
      name: 'HQ NanoStation Receiver 3',
      type: 'nanostation',
      status: 'offline',
      manufacturer: 'Ubiquiti',
      model: 'NanoStation Loco M5',
      ipAddress: '192.168.10.103',
      locationId: hqLocationId,
      metadata: {
        role: 'access_point',
        deploymentState: 'planned',
        frequencyBand: '5GHz',
        wirelessMode: 'bridge',
        assignedSector: 3,
      },
    },
    {
      assetId: hqNanoFourAsset.id,
      deviceCode: 'DEV-NANO-HQ-004',
      name: 'HQ NanoStation Receiver 4',
      type: 'nanostation',
      status: 'offline',
      manufacturer: 'Ubiquiti',
      model: 'NanoStation Loco M5',
      ipAddress: '192.168.10.104',
      locationId: hqLocationId,
      metadata: {
        role: 'access_point',
        deploymentState: 'planned',
        frequencyBand: '5GHz',
        wirelessMode: 'bridge',
        assignedSector: 4,
      },
    },
    {
      assetId: serverAsset.id,
      deviceCode: 'DEV-SERVER-HQ-001',
      name: 'MCC Smart City Backend Server',
      type: 'server',
      status: 'offline',
      ipAddress: '192.168.10.10',
      locationId: hqLocationId,
      metadata: {
        role: 'backend_server',
        deploymentState: 'planned',
        services: [
          'api',
          'database',
          'websocket_gateway',
          'telemetry_processing',
        ],
      },
    },
    {
      assetId: switchAsset.id,
      deviceCode: 'DEV-SWITCH-HQ-001',
      name: 'MCC Smart City Managed Network Switch',
      type: 'network_switch',
      status: 'offline',
      ipAddress: '192.168.10.2',
      locationId: hqLocationId,
      metadata: {
        role: 'core_network_switch',
        deploymentState: 'planned',
        managed: true,
      },
    },
    {
      assetId: upsAsset.id,
      deviceCode: 'DEV-UPS-HQ-001',
      name: 'MCC Smart City Server UPS',
      type: 'ups',
      status: 'offline',
      locationId: hqLocationId,
      metadata: {
        role: 'backup_power',
        deploymentState: 'planned',
        protects: [
          'DEV-SERVER-HQ-001',
          'DEV-JETSON-HQ-001',
          'DEV-SWITCH-HQ-001',
        ],
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 001
    |--------------------------------------------------------------------------
    */

    {
      assetId: cameraOneAsset.id,
      deviceCode: 'DEV-CAMERA-FIELD-001',
      name: 'Field Site 1 PTZ Camera',
      type: 'camera',
      status: 'offline',
      manufacturer: 'V380',
      model: 'SC31 PTZ',
      ipAddress: '192.168.20.11',
      locationId: fieldSiteOneId,
      metadata: {
        role: 'video_surveillance',
        deploymentState: 'testing',
        cameraCapabilities: {
          panTilt: true,
          nightVision: true,
          ethernet: true,
        },
        observedServicePort: 8800,
      },
    },
    {
      assetId: fieldNanoOneAsset.id,
      deviceCode: 'DEV-NANO-FIELD-001',
      name: 'Field Site 1 NanoStation',
      type: 'nanostation',
      status: 'offline',
      manufacturer: 'Ubiquiti',
      model: 'NanoStation Loco M5',
      ipAddress: '192.168.20.2',
      locationId: fieldSiteOneId,
      metadata: {
        role: 'station',
        deploymentState: 'planned',
        frequencyBand: '5GHz',
        wirelessMode: 'bridge',
        expectedPeerDeviceCode: 'DEV-NANO-HQ-001',
      },
    },

    /*
    |--------------------------------------------------------------------------
    | FIELD SITE 002
    |--------------------------------------------------------------------------
    */

    {
      assetId: cameraTwoAsset.id,
      deviceCode: 'DEV-CAMERA-FIELD-002',
      name: 'Field Site 2 Camera',
      type: 'camera',
      status: 'offline',
      locationId: fieldSiteTwoId,
      metadata: {
        role: 'video_surveillance',
        deploymentState: 'planned',
      },
    },
    {
      assetId: fieldNanoTwoAsset.id,
      deviceCode: 'DEV-NANO-FIELD-002',
      name: 'Field Site 2 NanoStation',
      type: 'nanostation',
      status: 'offline',
      manufacturer: 'Ubiquiti',
      model: 'NanoStation Loco M5',
      ipAddress: '192.168.30.2',
      locationId: fieldSiteTwoId,
      metadata: {
        role: 'station',
        deploymentState: 'planned',
        frequencyBand: '5GHz',
        wirelessMode: 'bridge',
        expectedPeerDeviceCode: 'DEV-NANO-HQ-002',
      },
    },
  ];

  await db.insert(devices).values(deviceRecords).onConflictDoNothing();

  console.log('Devices seeded.');
}
