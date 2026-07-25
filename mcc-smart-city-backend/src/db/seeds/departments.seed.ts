import { db } from '../index';
import { departments } from '../schema';

export async function seedDepartments(): Promise<void> {
  console.log('Seeding departments...');

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

  console.log('Departments seeded.');
}
