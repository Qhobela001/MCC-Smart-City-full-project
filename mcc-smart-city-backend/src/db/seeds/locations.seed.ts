import { db } from '../index';
import { locations } from '../schema';

export async function seedLocations(): Promise<void> {
  console.log('Seeding locations...');

  await db
    .insert(locations)
    .values([
      {
        name: 'MCC Headquarters',
        locationCode: 'MCC-HQ',
        address: 'Maseru City Council Headquarters',
        district: 'Maseru Central',
        description:
          'Primary command centre, backend infrastructure, AI processing and monitoring location.',
        isActive: true,
      },
      {
        name: 'Pioneer Road Camera Site',
        locationCode: 'FIELD-SITE-001',
        address: 'Pioneer Road, Maseru',
        district: 'Maseru Central',
        description:
          'Initial field monitoring site for public safety, illegal dumping and traffic observation.',
        isActive: true,
      },
      {
        name: 'Kingsway Camera Site',
        locationCode: 'FIELD-SITE-002',
        address: 'Kingsway, Maseru',
        district: 'Maseru Central',
        description:
          'Planned CBD monitoring site for public safety and municipal operations.',
        isActive: true,
      },
    ])
    .onConflictDoNothing();

  console.log('Locations seeded.');
}
