import { db } from '../index';
import { serviceLevelProfiles } from '../schema';

export async function seedServiceLevelProfiles(): Promise<void> {
  console.log('Seeding service-level profiles...');

  const profiles = [
    {
      profileCode: 'CRITICAL_EMERGENCY',
      name: 'Critical Emergency',
      description:
        'Immediate response profile for fire, major accidents, building collapse and other life-threatening emergencies.',
      acknowledgementTargetMinutes: 5,
      responseTargetMinutes: 10,
      resolutionTargetMinutes: 120,
      escalationAfterMinutes: 5,
      isActive: true,
      metadata: {
        operationalClass: 'emergency',
      },
    },
    {
      profileCode: 'HIGH_PRIORITY',
      name: 'High Priority Response',
      description:
        'Urgent response profile for serious safety, infrastructure and environmental incidents.',
      acknowledgementTargetMinutes: 15,
      responseTargetMinutes: 30,
      resolutionTargetMinutes: 480,
      escalationAfterMinutes: 15,
      isActive: true,
      metadata: {
        operationalClass: 'urgent',
      },
    },
    {
      profileCode: 'STANDARD_MUNICIPAL',
      name: 'Standard Municipal Response',
      description:
        'Standard response profile for ordinary municipal incidents requiring action within one working day.',
      acknowledgementTargetMinutes: 30,
      responseTargetMinutes: 120,
      resolutionTargetMinutes: 1440,
      escalationAfterMinutes: 60,
      isActive: true,
      metadata: {
        operationalClass: 'standard',
      },
    },
    {
      profileCode: 'LOW_PRIORITY',
      name: 'Low Priority Response',
      description:
        'Response profile for non-urgent complaints and minor service issues.',
      acknowledgementTargetMinutes: 60,
      responseTargetMinutes: 480,
      resolutionTargetMinutes: 4320,
      escalationAfterMinutes: 240,
      isActive: true,
      metadata: {
        operationalClass: 'non_urgent',
      },
    },
  ] as const;

  for (const profile of profiles) {
    await db
      .insert(serviceLevelProfiles)
      .values(profile)
      .onConflictDoUpdate({
        target: serviceLevelProfiles.profileCode,
        set: {
          name: profile.name,
          description: profile.description,
          acknowledgementTargetMinutes: profile.acknowledgementTargetMinutes,
          responseTargetMinutes: profile.responseTargetMinutes,
          resolutionTargetMinutes: profile.resolutionTargetMinutes,
          escalationAfterMinutes: profile.escalationAfterMinutes,
          isActive: profile.isActive,
          metadata: profile.metadata,
          updatedAt: new Date(),
        },
      });
  }

  console.log('Service-level profiles seeded.');
}
