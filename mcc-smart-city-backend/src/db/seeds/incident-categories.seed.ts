import { db } from '../index';
import { incidentCategories } from '../schema';

export async function seedIncidentCategories(): Promise<void> {
  console.log('Seeding incident categories...');

  const categories = [
    {
      categoryCode: 'ENVIRONMENTAL',
      name: 'Environmental',
      description:
        'Waste management, sanitation, pollution and environmental health incidents.',
      displayOrder: 1,
      isActive: true,
      metadata: {},
    },
    {
      categoryCode: 'ROADS_TRANSPORT',
      name: 'Roads and Transport',
      description:
        'Road conditions, traffic infrastructure and transport-related incidents.',
      displayOrder: 2,
      isActive: true,
      metadata: {},
    },
    {
      categoryCode: 'PUBLIC_SAFETY',
      name: 'Public Safety',
      description:
        'Security, unlawful activity, vandalism and public-order incidents.',
      displayOrder: 3,
      isActive: true,
      metadata: {},
    },
    {
      categoryCode: 'UTILITIES',
      name: 'Utilities',
      description:
        'Streetlighting, electricity, water and municipal utility incidents.',
      displayOrder: 4,
      isActive: true,
      metadata: {},
    },
    {
      categoryCode: 'EMERGENCY',
      name: 'Emergency',
      description:
        'Fire, flooding, serious accidents and disaster-related incidents.',
      displayOrder: 5,
      isActive: true,
      metadata: {},
    },
    {
      categoryCode: 'GENERAL',
      name: 'General Services',
      description:
        'General municipal complaints and incidents not covered by another category.',
      displayOrder: 6,
      isActive: true,
      metadata: {},
    },
  ] as const;

  for (const category of categories) {
    await db
      .insert(incidentCategories)
      .values(category)
      .onConflictDoUpdate({
        target: incidentCategories.categoryCode,
        set: {
          name: category.name,
          description: category.description,
          displayOrder: category.displayOrder,
          isActive: category.isActive,
          metadata: category.metadata,
          updatedAt: new Date(),
        },
      });
  }

  console.log('Incident categories seeded.');
}
