import 'dotenv/config';
import { db } from './index';
import { departments, roles } from './schema';

async function seed(): Promise<void> {
  console.log('Starting database seed...');

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

  await db
    .insert(departments)
    .values([
      {
        name: 'Information and Communication Technology',
        code: 'ICT',
        description:
          'Responsible for platform administration and infrastructure.',
      },
      {
        name: 'Municipal Operations',
        code: 'OPS',
        description: 'Responsible for monitoring and incident coordination.',
      },
      {
        name: 'Security Services',
        code: 'SEC',
        description:
          'Responsible for public safety and surveillance operations.',
      },
      {
        name: 'Public Works',
        code: 'PWO',
        description:
          'Responsible for infrastructure and municipal maintenance.',
      },
      {
        name: 'Environmental Health',
        code: 'ENV',
        description:
          'Responsible for waste, pollution and environmental incidents.',
      },
    ])
    .onConflictDoNothing();

  console.log('Database seed completed successfully.');
}

seed().catch((error: unknown) => {
  console.error('Database seed failed:', error);
  process.exitCode = 1;
});
