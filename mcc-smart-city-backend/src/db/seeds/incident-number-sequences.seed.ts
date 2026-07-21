import { db } from '../index';
import { incidentNumberSequences } from '../schema';

export async function seedIncidentNumberSequences(): Promise<void> {
  console.log('Seeding incident-number sequences...');

  const currentYear = new Date().getFullYear();

  await db
    .insert(incidentNumberSequences)
    .values({
      year: currentYear,
      prefix: 'INC',
      lastNumber: 0,
      paddingLength: 6,
    })
    .onConflictDoNothing({
      target: incidentNumberSequences.year,
    });

  console.log(`Incident-number sequence for ${currentYear} is available.`);
}
