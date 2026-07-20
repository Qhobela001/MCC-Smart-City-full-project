import { eq } from 'drizzle-orm';

import { db } from '../index';
import { devices, nanostations } from '../schema';

type NanoStationInsert = typeof nanostations.$inferInsert;

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

export async function seedNanoStations(): Promise<void> {
  console.log('Seeding NanoStations...');

  const [hq1, hq2, hq3, hq4, field1, field2] = await Promise.all([
    getDeviceId('DEV-NANO-HQ-001'),
    getDeviceId('DEV-NANO-HQ-002'),
    getDeviceId('DEV-NANO-HQ-003'),
    getDeviceId('DEV-NANO-HQ-004'),
    getDeviceId('DEV-NANO-FIELD-001'),
    getDeviceId('DEV-NANO-FIELD-002'),
  ]);

  const records: NanoStationInsert[] = [
    {
      deviceId: hq1,
      role: 'receiver',
      wirelessMode: 'bridge',
      ssid: 'MCC-HQ-SECTOR-01',
      frequencyMhz: 5805,
      channelWidthMhz: 40,
      airmaxEnabled: true,
      managementUrl: 'https://192.168.10.101',
      antennaGainDbi: '13',
    },
    {
      deviceId: hq2,
      role: 'receiver',
      wirelessMode: 'bridge',
      ssid: 'MCC-HQ-SECTOR-02',
      frequencyMhz: 5825,
      channelWidthMhz: 40,
      airmaxEnabled: true,
      managementUrl: 'https://192.168.10.102',
      antennaGainDbi: '13',
    },
    {
      deviceId: hq3,
      role: 'receiver',
      wirelessMode: 'bridge',
      ssid: 'MCC-HQ-SECTOR-03',
      frequencyMhz: 5765,
      channelWidthMhz: 40,
      airmaxEnabled: true,
      managementUrl: 'https://192.168.10.103',
      antennaGainDbi: '13',
    },
    {
      deviceId: hq4,
      role: 'receiver',
      wirelessMode: 'bridge',
      ssid: 'MCC-HQ-SECTOR-04',
      frequencyMhz: 5785,
      channelWidthMhz: 40,
      airmaxEnabled: true,
      managementUrl: 'https://192.168.10.104',
      antennaGainDbi: '13',
    },

    {
      deviceId: field1,
      role: 'station',
      wirelessMode: 'station',
      ssid: 'MCC-HQ-SECTOR-01',
      frequencyMhz: 5805,
      channelWidthMhz: 40,
      airmaxEnabled: true,
      managementUrl: 'https://192.168.20.2',
      antennaGainDbi: '13',
    },

    {
      deviceId: field2,
      role: 'station',
      wirelessMode: 'station',
      ssid: 'MCC-HQ-SECTOR-02',
      frequencyMhz: 5825,
      channelWidthMhz: 40,
      airmaxEnabled: true,
      managementUrl: 'https://192.168.30.2',
      antennaGainDbi: '13',
    },
  ];

  await db.insert(nanostations).values(records).onConflictDoNothing();

  console.log('NanoStations seeded.');
}
