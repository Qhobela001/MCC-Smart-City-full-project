import {
  pgTable,
  pgEnum,
  uuid,
  varchar,
  text,
  timestamp,
  boolean,
  jsonb,
  numeric,
} from 'drizzle-orm/pg-core';

/*
|--------------------------------------------------------------------------
| ENUMS
|--------------------------------------------------------------------------
*/

export const userStatusEnum = pgEnum('user_status', [
  'active',
  'inactive',
  'suspended',
]);

export const deviceStatusEnum = pgEnum('device_status', [
  'online',
  'offline',
  'maintenance',
  'faulty',
  'decommissioned',
]);

export const deviceTypeEnum = pgEnum('device_type', [
  'camera',
  'jetson',
  'nanostation',
  'server',
  'network_switch',
  'ups',
  'solar_controller',
  'other',
]);

/*
|--------------------------------------------------------------------------
| ROLES
|--------------------------------------------------------------------------
*/

export const roles = pgTable('roles', {
  id: uuid('id').defaultRandom().primaryKey(),

  name: varchar('name', { length: 100 }).notNull().unique(),

  description: text('description'),

  isSystemRole: boolean('is_system_role').default(false).notNull(),

  createdAt: timestamp('created_at').defaultNow().notNull(),

  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

/*
|--------------------------------------------------------------------------
| DEPARTMENTS
|--------------------------------------------------------------------------
*/

export const departments = pgTable('departments', {
  id: uuid('id').defaultRandom().primaryKey(),

  name: varchar('name', { length: 100 }).notNull().unique(),

  code: varchar('code', { length: 20 }).notNull().unique(),

  description: text('description'),

  createdAt: timestamp('created_at').defaultNow().notNull(),

  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

/*
|--------------------------------------------------------------------------
| USERS
|--------------------------------------------------------------------------
*/

export const users = pgTable('users', {
  id: uuid('id').defaultRandom().primaryKey(),

  fullName: varchar('full_name', {
    length: 150,
  }).notNull(),

  email: varchar('email', {
    length: 255,
  })
    .notNull()
    .unique(),

  employeeNumber: varchar('employee_number', {
    length: 50,
  }),

  phoneNumber: varchar('phone_number', {
    length: 30,
  }),

  status: userStatusEnum('status').default('active').notNull(),

  roleId: uuid('role_id').references(() => roles.id),

  departmentId: uuid('department_id').references(() => departments.id),

  createdAt: timestamp('created_at').defaultNow().notNull(),

  updatedAt: timestamp('updated_at').defaultNow().notNull(),
});

/*
|--------------------------------------------------------------------------
| LOCATIONS
|--------------------------------------------------------------------------
|
| Stores physical installation and incident locations across Maseru.
|--------------------------------------------------------------------------
*/

export const locations = pgTable('locations', {
  id: uuid('id').defaultRandom().primaryKey(),

  name: varchar('name', {
    length: 160,
  }).notNull(),

  locationCode: varchar('location_code', {
    length: 50,
  })
    .notNull()
    .unique(),

  address: text('address'),

  district: varchar('district', {
    length: 120,
  }),

  latitude: numeric('latitude', {
    precision: 10,
    scale: 7,
  }),

  longitude: numeric('longitude', {
    precision: 10,
    scale: 7,
  }),

  description: text('description'),

  isActive: boolean('is_active').default(true).notNull(),

  createdAt: timestamp('created_at', {
    withTimezone: true,
  })
    .defaultNow()
    .notNull(),

  updatedAt: timestamp('updated_at', {
    withTimezone: true,
  })
    .defaultNow()
    .notNull(),
});

/*
|--------------------------------------------------------------------------
| DEVICES
|--------------------------------------------------------------------------
|
| Parent inventory table for physical smart-city equipment.
|--------------------------------------------------------------------------
*/

export const devices = pgTable('devices', {
  id: uuid('id').defaultRandom().primaryKey(),

  deviceCode: varchar('device_code', {
    length: 80,
  })
    .notNull()
    .unique(),

  name: varchar('name', {
    length: 160,
  }).notNull(),

  type: deviceTypeEnum('type').notNull(),

  status: deviceStatusEnum('status').default('offline').notNull(),

  manufacturer: varchar('manufacturer', {
    length: 120,
  }),

  model: varchar('model', {
    length: 120,
  }),

  serialNumber: varchar('serial_number', {
    length: 120,
  }).unique(),

  ipAddress: varchar('ip_address', {
    length: 45,
  }),

  macAddress: varchar('mac_address', {
    length: 30,
  }),

  firmwareVersion: varchar('firmware_version', {
    length: 80,
  }),

  locationId: uuid('location_id').references(() => locations.id, {
    onDelete: 'set null',
    onUpdate: 'cascade',
  }),

  installedAt: timestamp('installed_at', {
    withTimezone: true,
  }),

  lastSeenAt: timestamp('last_seen_at', {
    withTimezone: true,
  }),

  metadata: jsonb('metadata')
    .$type<Record<string, unknown>>()
    .default({})
    .notNull(),

  createdAt: timestamp('created_at', {
    withTimezone: true,
  })
    .defaultNow()
    .notNull(),

  updatedAt: timestamp('updated_at', {
    withTimezone: true,
  })
    .defaultNow()
    .notNull(),
});

/*
|--------------------------------------------------------------------------
| CAMERAS
|--------------------------------------------------------------------------
|
| Stores camera-specific properties.
| Every camera must also have a matching row in devices.
|--------------------------------------------------------------------------
*/

export const cameras = pgTable('cameras', {
  id: uuid('id').defaultRandom().primaryKey(),

  deviceId: uuid('device_id')
    .notNull()
    .unique()
    .references(() => devices.id, {
      onDelete: 'restrict',
      onUpdate: 'cascade',
    }),

  cameraCode: varchar('camera_code', {
    length: 80,
  })
    .notNull()
    .unique(),

  rtspUrl: text('rtsp_url'),

  streamPath: text('stream_path'),

  streamUsername: varchar('stream_username', {
    length: 120,
  }),

  isAiEnabled: boolean('is_ai_enabled').default(true).notNull(),

  isRecordingEnabled: boolean('is_recording_enabled').default(true).notNull(),

  assignedJetsonId: uuid('assigned_jetson_id').references(() => devices.id, {
    onDelete: 'set null',
    onUpdate: 'cascade',
  }),

  fieldOfViewDescription: text('field_of_view_description'),

  createdAt: timestamp('created_at', {
    withTimezone: true,
  })
    .defaultNow()
    .notNull(),

  updatedAt: timestamp('updated_at', {
    withTimezone: true,
  })
    .defaultNow()
    .notNull(),
});
