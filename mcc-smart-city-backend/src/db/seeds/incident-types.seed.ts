import { eq, inArray } from 'drizzle-orm';

import { db } from '../index';
import {
  departments,
  incidentCategories,
  incidentTypes,
  serviceLevelProfiles,
} from '../schema';

type Priority = 'low' | 'medium' | 'high' | 'critical';

interface IncidentTypeSeed {
  incidentTypeCode: string;
  name: string;
  description: string;
  categoryCode: string;
  departmentCode: string;
  serviceLevelProfileCode: string;
  defaultPriority: Priority;
  isAiDetectable: boolean;
  evidenceRequired: boolean;
  supervisorVerificationRequired: boolean;
  publicReportingAllowed: boolean;
  automaticIncidentCreationAllowed: boolean;
  minimumAutomaticConfidence: string | null;
  displayOrder: number;
  metadata: Record<string, unknown>;
}

export async function seedIncidentTypes(): Promise<void> {
  console.log('Seeding incident types...');

  const requiredDepartmentCodes = ['ENV', 'PWO', 'SEC', 'OPS'];

  const departmentRows = await db
    .select({
      id: departments.id,
      code: departments.code,
    })
    .from(departments)
    .where(inArray(departments.code, requiredDepartmentCodes));

  const categoryRows = await db
    .select({
      id: incidentCategories.id,
      code: incidentCategories.categoryCode,
    })
    .from(incidentCategories);

  const profileRows = await db
    .select({
      id: serviceLevelProfiles.id,
      code: serviceLevelProfiles.profileCode,
    })
    .from(serviceLevelProfiles);

  const departmentByCode = new Map(
    departmentRows.map((department) => [department.code, department.id]),
  );

  const categoryByCode = new Map(
    categoryRows.map((category) => [category.code, category.id]),
  );

  const profileByCode = new Map(
    profileRows.map((profile) => [profile.code, profile.id]),
  );

  for (const departmentCode of requiredDepartmentCodes) {
    if (!departmentByCode.has(departmentCode)) {
      throw new Error(
        `Cannot seed incident types: department ${departmentCode} does not exist.`,
      );
    }
  }

  const requiredCategoryCodes = [
    'ENVIRONMENTAL',
    'ROADS_TRANSPORT',
    'PUBLIC_SAFETY',
    'UTILITIES',
    'EMERGENCY',
    'GENERAL',
  ];

  for (const categoryCode of requiredCategoryCodes) {
    if (!categoryByCode.has(categoryCode)) {
      throw new Error(
        `Cannot seed incident types: category ${categoryCode} does not exist.`,
      );
    }
  }

  const requiredProfileCodes = [
    'CRITICAL_EMERGENCY',
    'HIGH_PRIORITY',
    'STANDARD_MUNICIPAL',
    'LOW_PRIORITY',
  ];

  for (const profileCode of requiredProfileCodes) {
    if (!profileByCode.has(profileCode)) {
      throw new Error(
        `Cannot seed incident types: service-level profile ${profileCode} does not exist.`,
      );
    }
  }

  const incidentTypeSeeds: IncidentTypeSeed[] = [
    {
      incidentTypeCode: 'ILLEGAL_DUMPING',
      name: 'Illegal Dumping',
      description:
        'Unauthorized disposal of waste on roadsides, public land or other prohibited locations.',
      categoryCode: 'ENVIRONMENTAL',
      departmentCode: 'ENV',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: true,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: '0.8500',
      displayOrder: 1,
      metadata: {},
    },
    {
      incidentTypeCode: 'OVERFLOWING_WASTE_CONTAINER',
      name: 'Overflowing Waste Container',
      description:
        'A municipal waste container or skip that has exceeded its safe capacity.',
      categoryCode: 'ENVIRONMENTAL',
      departmentCode: 'ENV',
      serviceLevelProfileCode: 'STANDARD_MUNICIPAL',
      defaultPriority: 'medium',
      isAiDetectable: true,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: '0.8500',
      displayOrder: 2,
      metadata: {},
    },
    {
      incidentTypeCode: 'PUBLIC_URINATION',
      name: 'Public Urination',
      description:
        'A sanitation or public-order incident involving urination in a public area.',
      categoryCode: 'ENVIRONMENTAL',
      departmentCode: 'ENV',
      serviceLevelProfileCode: 'STANDARD_MUNICIPAL',
      defaultPriority: 'medium',
      isAiDetectable: true,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: '0.9000',
      displayOrder: 3,
      metadata: {
        sensitiveEvidence: true,
      },
    },
    {
      incidentTypeCode: 'NOISE_POLLUTION',
      name: 'Noise Pollution',
      description:
        'Excessive noise exceeding acceptable municipal or environmental limits.',
      categoryCode: 'ENVIRONMENTAL',
      departmentCode: 'ENV',
      serviceLevelProfileCode: 'STANDARD_MUNICIPAL',
      defaultPriority: 'medium',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 4,
      metadata: {},
    },
    {
      incidentTypeCode: 'AIR_POLLUTION',
      name: 'Air Pollution',
      description:
        'Smoke, emissions or airborne contaminants affecting public health.',
      categoryCode: 'ENVIRONMENTAL',
      departmentCode: 'ENV',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 5,
      metadata: {},
    },
    {
      incidentTypeCode: 'DEAD_ANIMAL',
      name: 'Dead Animal',
      description:
        'A dead animal requiring removal from a road, pavement or public area.',
      categoryCode: 'ENVIRONMENTAL',
      departmentCode: 'ENV',
      serviceLevelProfileCode: 'STANDARD_MUNICIPAL',
      defaultPriority: 'medium',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 6,
      metadata: {},
    },
    {
      incidentTypeCode: 'POTHOLE',
      name: 'Pothole',
      description:
        'A damaged road surface containing a hole or significant structural defect.',
      categoryCode: 'ROADS_TRANSPORT',
      departmentCode: 'PWO',
      serviceLevelProfileCode: 'STANDARD_MUNICIPAL',
      defaultPriority: 'medium',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 1,
      metadata: {},
    },
    {
      incidentTypeCode: 'ROAD_OBSTRUCTION',
      name: 'Road Obstruction',
      description:
        'An object, vehicle or other obstruction interfering with safe road use.',
      categoryCode: 'ROADS_TRANSPORT',
      departmentCode: 'PWO',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 2,
      metadata: {},
    },
    {
      incidentTypeCode: 'DAMAGED_ROAD_SIGN',
      name: 'Damaged Road Sign',
      description:
        'A missing, damaged, obscured or unsafe municipal road sign.',
      categoryCode: 'ROADS_TRANSPORT',
      departmentCode: 'PWO',
      serviceLevelProfileCode: 'STANDARD_MUNICIPAL',
      defaultPriority: 'medium',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 3,
      metadata: {},
    },
    {
      incidentTypeCode: 'TRAFFIC_SIGNAL_FAILURE',
      name: 'Traffic Signal Failure',
      description:
        'A traffic light or control signal that is malfunctioning or unavailable.',
      categoryCode: 'ROADS_TRANSPORT',
      departmentCode: 'PWO',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 4,
      metadata: {},
    },
    {
      incidentTypeCode: 'SUSPICIOUS_ACTIVITY',
      name: 'Suspicious Activity',
      description:
        'Observed behaviour or activity that may present a public-safety risk.',
      categoryCode: 'PUBLIC_SAFETY',
      departmentCode: 'SEC',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: true,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: '0.9000',
      displayOrder: 1,
      metadata: {
        sensitiveEvidence: true,
      },
    },
    {
      incidentTypeCode: 'VANDALISM',
      name: 'Vandalism',
      description:
        'Intentional damage to municipal assets, property or public infrastructure.',
      categoryCode: 'PUBLIC_SAFETY',
      departmentCode: 'SEC',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 2,
      metadata: {},
    },
    {
      incidentTypeCode: 'UNAUTHORIZED_STREET_VENDING',
      name: 'Unauthorized Street Vending',
      description:
        'Street vending taking place without authorization or in a restricted area.',
      categoryCode: 'PUBLIC_SAFETY',
      departmentCode: 'SEC',
      serviceLevelProfileCode: 'STANDARD_MUNICIPAL',
      defaultPriority: 'medium',
      isAiDetectable: true,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: '0.9000',
      displayOrder: 3,
      metadata: {},
    },
    {
      incidentTypeCode: 'PUBLIC_DISTURBANCE',
      name: 'Public Disturbance',
      description:
        'Disorderly conduct, fighting or other behaviour disturbing public order.',
      categoryCode: 'PUBLIC_SAFETY',
      departmentCode: 'SEC',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 4,
      metadata: {},
    },
    {
      incidentTypeCode: 'STREETLIGHT_FAILURE',
      name: 'Streetlight Failure',
      description:
        'A municipal streetlight that is damaged, malfunctioning or not operating.',
      categoryCode: 'UTILITIES',
      departmentCode: 'PWO',
      serviceLevelProfileCode: 'STANDARD_MUNICIPAL',
      defaultPriority: 'medium',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 1,
      metadata: {},
    },
    {
      incidentTypeCode: 'WATER_LEAK',
      name: 'Water Leak',
      description:
        'A visible water leak affecting a road, public facility or municipal area.',
      categoryCode: 'UTILITIES',
      departmentCode: 'PWO',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 2,
      metadata: {},
    },
    {
      incidentTypeCode: 'POWER_FAILURE',
      name: 'Power Failure',
      description:
        'Loss of electrical power affecting municipal infrastructure or public services.',
      categoryCode: 'UTILITIES',
      departmentCode: 'PWO',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 3,
      metadata: {},
    },
    {
      incidentTypeCode: 'DAMAGED_UTILITY_POLE',
      name: 'Damaged Utility Pole',
      description:
        'A damaged, unstable or unsafe pole supporting municipal infrastructure.',
      categoryCode: 'UTILITIES',
      departmentCode: 'PWO',
      serviceLevelProfileCode: 'HIGH_PRIORITY',
      defaultPriority: 'high',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 4,
      metadata: {},
    },
    {
      incidentTypeCode: 'FIRE',
      name: 'Fire',
      description:
        'A confirmed or suspected fire requiring immediate emergency coordination.',
      categoryCode: 'EMERGENCY',
      departmentCode: 'OPS',
      serviceLevelProfileCode: 'CRITICAL_EMERGENCY',
      defaultPriority: 'critical',
      isAiDetectable: true,
      evidenceRequired: true,
      supervisorVerificationRequired: false,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: '0.9000',
      displayOrder: 1,
      metadata: {},
    },
    {
      incidentTypeCode: 'FLOODING',
      name: 'Flooding',
      description:
        'Floodwater affecting roads, homes, public land or municipal infrastructure.',
      categoryCode: 'EMERGENCY',
      departmentCode: 'OPS',
      serviceLevelProfileCode: 'CRITICAL_EMERGENCY',
      defaultPriority: 'critical',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: false,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 2,
      metadata: {},
    },
    {
      incidentTypeCode: 'BUILDING_COLLAPSE',
      name: 'Building Collapse',
      description:
        'A partial or complete structural collapse requiring emergency coordination.',
      categoryCode: 'EMERGENCY',
      departmentCode: 'OPS',
      serviceLevelProfileCode: 'CRITICAL_EMERGENCY',
      defaultPriority: 'critical',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: false,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 3,
      metadata: {},
    },
    {
      incidentTypeCode: 'TRAFFIC_ACCIDENT',
      name: 'Traffic Accident',
      description:
        'A collision or road accident requiring municipal operational response.',
      categoryCode: 'EMERGENCY',
      departmentCode: 'OPS',
      serviceLevelProfileCode: 'CRITICAL_EMERGENCY',
      defaultPriority: 'critical',
      isAiDetectable: false,
      evidenceRequired: true,
      supervisorVerificationRequired: false,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 4,
      metadata: {},
    },
    {
      incidentTypeCode: 'GENERAL_COMPLAINT',
      name: 'General Complaint',
      description:
        'A general municipal service complaint requiring review and classification.',
      categoryCode: 'GENERAL',
      departmentCode: 'OPS',
      serviceLevelProfileCode: 'LOW_PRIORITY',
      defaultPriority: 'low',
      isAiDetectable: false,
      evidenceRequired: false,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 1,
      metadata: {},
    },
    {
      incidentTypeCode: 'OTHER',
      name: 'Other Incident',
      description:
        'An incident that does not yet match an existing configured incident type.',
      categoryCode: 'GENERAL',
      departmentCode: 'OPS',
      serviceLevelProfileCode: 'STANDARD_MUNICIPAL',
      defaultPriority: 'medium',
      isAiDetectable: false,
      evidenceRequired: false,
      supervisorVerificationRequired: true,
      publicReportingAllowed: true,
      automaticIncidentCreationAllowed: false,
      minimumAutomaticConfidence: null,
      displayOrder: 2,
      metadata: {},
    },
  ];

  for (const incidentType of incidentTypeSeeds) {
    const categoryId = categoryByCode.get(incidentType.categoryCode);
    const responsibleDepartmentId = departmentByCode.get(
      incidentType.departmentCode,
    );
    const serviceLevelProfileId = profileByCode.get(
      incidentType.serviceLevelProfileCode,
    );

    if (!categoryId || !responsibleDepartmentId || !serviceLevelProfileId) {
      throw new Error(
        `Unable to resolve dependencies for incident type ${incidentType.incidentTypeCode}.`,
      );
    }

    await db
      .insert(incidentTypes)
      .values({
        categoryId,
        incidentTypeCode: incidentType.incidentTypeCode,
        name: incidentType.name,
        description: incidentType.description,
        defaultPriority: incidentType.defaultPriority,
        responsibleDepartmentId,
        serviceLevelProfileId,
        isAiDetectable: incidentType.isAiDetectable,
        evidenceRequired: incidentType.evidenceRequired,
        supervisorVerificationRequired:
          incidentType.supervisorVerificationRequired,
        publicReportingAllowed: incidentType.publicReportingAllowed,
        automaticIncidentCreationAllowed:
          incidentType.automaticIncidentCreationAllowed,
        minimumAutomaticConfidence: incidentType.minimumAutomaticConfidence,
        displayOrder: incidentType.displayOrder,
        isActive: true,
        metadata: incidentType.metadata,
      })
      .onConflictDoUpdate({
        target: incidentTypes.incidentTypeCode,
        set: {
          categoryId,
          name: incidentType.name,
          description: incidentType.description,
          defaultPriority: incidentType.defaultPriority,
          responsibleDepartmentId,
          serviceLevelProfileId,
          isAiDetectable: incidentType.isAiDetectable,
          evidenceRequired: incidentType.evidenceRequired,
          supervisorVerificationRequired:
            incidentType.supervisorVerificationRequired,
          publicReportingAllowed: incidentType.publicReportingAllowed,
          automaticIncidentCreationAllowed:
            incidentType.automaticIncidentCreationAllowed,
          minimumAutomaticConfidence: incidentType.minimumAutomaticConfidence,
          displayOrder: incidentType.displayOrder,
          isActive: true,
          metadata: incidentType.metadata,
          updatedAt: new Date(),
        },
      });
  }

  const seededTypes = await db
    .select({
      code: incidentTypes.incidentTypeCode,
    })
    .from(incidentTypes)
    .where(eq(incidentTypes.isActive, true));

  console.log(
    `Incident types seeded. Active incident type count: ${seededTypes.length}.`,
  );
}
