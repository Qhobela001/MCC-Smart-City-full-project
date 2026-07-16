import 'dotenv/config';
import { seedDepartments } from './seeds/departments.seed';
import { seedLocations } from './seeds/locations.seed';
import { seedRoles } from './seeds/roles.seed';

async function seed(): Promise<void> {
  console.log('Starting database seed...');

  await seedRoles();
  await seedDepartments();
  await seedLocations();

  console.log('Database seed completed successfully.');
}

seed().catch((error: unknown) => {
  console.error('Database seed failed:', error);
  process.exitCode = 1;
});
