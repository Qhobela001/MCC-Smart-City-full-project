import { db } from '../index';
import { roles } from '../schema';

export async function seedRoles(): Promise<void> {
  console.log('Seeding roles...');

  await db
    .insert(roles)
    .values([
      {
        name: 'Super Administrator',
        description: 'Full access to the entire MCC Smart City platform.',
        isSystemRole: true,
      },
      {
        name: 'Administrator',
        description: 'Manages users, devices, cameras, incidents and reports.',
        isSystemRole: true,
      },
      {
        name: 'Operations Manager',
        description:
          'Reviews incidents, assigns officers and oversees operations.',
        isSystemRole: true,
      },
      {
        name: 'Monitoring Officer',
        description: 'Monitors live feeds and verifies alerts.',
        isSystemRole: true,
      },
      {
        name: 'Field Officer',
        description: 'Responds to assigned incidents and submits evidence.',
        isSystemRole: true,
      },
      {
        name: 'Maintenance Technician',
        description:
          'Maintains cameras, Jetsons, NanoStations and related hardware.',
        isSystemRole: true,
      },
      {
        name: 'Auditor',
        description:
          'Read-only access to reports, incidents and audit records.',
        isSystemRole: true,
      },
    ])
    .onConflictDoNothing();

  console.log('Roles seeded.');
}
