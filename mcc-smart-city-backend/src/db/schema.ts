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
  integer,
  index,
} from 'drizzle-orm/pg-core';

/*
|--------------------------------------------------------------------------
| ENUMS
|--------------------------------------------------------------------------
*/

export const powerSystemStatusEnum = pgEnum('power_system_status', [
  'planned',
  'online',
  'degraded',
  'offline',
  'maintenance',
]);

export const powerSystemTypeEnum = pgEnum('power_system_type', [
  'solar_battery',
  'mains_ups',
  'hybrid',
  'other',
]);

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

export const networkLinkStatusEnum = pgEnum('network_link_status', [
  'online',
  'offline',
  'degraded',
  'maintenance',
]);

export const networkLinkTypeEnum = pgEnum('network_link_type', [
  'point_to_point',
  'point_to_multipoint',
  'ethernet',
  'wifi',
]);

export const streamStatusEnum = pgEnum('stream_status', [
  'available',
  'unavailable',
  'degraded',
  'disabled',
]);

export const jetsonWorkloadStatusEnum = pgEnum('jetson_workload_status', [
  'idle',
  'running',
  'overloaded',
  'error',
  'maintenance',
]);

export const assetTypeEnum = pgEnum('asset_type', [
  'camera',
  'jetson',
  'nanostation',
  'pole',
  'cabinet',
  'solar_panel',
  'battery',
  'charge_controller',
  'ups',
  'network_switch',
  'server',
  'other',
]);

export const assetStatusEnum = pgEnum('asset_status', [
  'planned',
  'installed',
  'operational',
  'maintenance',
  'retired',
]);

export const heartbeatStatusEnum = pgEnum('heartbeat_status', [
  'online',
  'offline',
  'degraded',
  'maintenance',
]);

export const eventSeverityEnum = pgEnum('event_severity', [
  'info',
  'warning',
  'critical',
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

/*This is the assets table*/

export const assets = pgTable('assets', {
  id: uuid('id').defaultRandom().primaryKey(),

  assetCode: varchar('asset_code', {
    length: 80,
  })
    .notNull()
    .unique(),

  assetName: varchar('asset_name', {
    length: 160,
  }).notNull(),

  assetType: assetTypeEnum('asset_type').notNull(),

  status: assetStatusEnum('status').default('planned').notNull(),

  manufacturer: varchar('manufacturer', {
    length: 120,
  }),

  model: varchar('model', {
    length: 120,
  }),

  serialNumber: varchar('serial_number', {
    length: 120,
  }),

  purchaseDate: timestamp('purchase_date', {
    withTimezone: true,
  }),

  installationDate: timestamp('installation_date', {
    withTimezone: true,
  }),

  warrantyExpiry: timestamp('warranty_expiry', {
    withTimezone: true,
  }),

  expectedLifeYears: integer('expected_life_years'),

  locationId: uuid('location_id').references(() => locations.id, {
    onDelete: 'set null',
    onUpdate: 'cascade',
  }),

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

  assetId: uuid('asset_id')
    .notNull()
    .unique()
    .references(() => assets.id, {
      onDelete: 'restrict',
      onUpdate: 'cascade',
    }),

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

/*This is the jetsonsNodes table*/

export const jetsonNodes = pgTable('jetson_nodes', {
  id: uuid('id').defaultRandom().primaryKey(),

  deviceId: uuid('device_id')
    .notNull()
    .unique()
    .references(() => devices.id, {
      onDelete: 'restrict',
      onUpdate: 'cascade',
    }),

  hostname: varchar('hostname', {
    length: 120,
  })
    .notNull()
    .unique(),

  jetpackVersion: varchar('jetpack_version', {
    length: 50,
  }),

  cudaVersion: varchar('cuda_version', {
    length: 50,
  }),

  tensorrtVersion: varchar('tensorrt_version', {
    length: 50,
  }),

  pythonVersion: varchar('python_version', {
    length: 50,
  }),

  workloadStatus: jetsonWorkloadStatusEnum('workload_status')
    .default('idle')
    .notNull(),

  maximumCameraStreams: integer('maximum_camera_streams').default(1).notNull(),

  activeCameraStreams: integer('active_camera_streams').default(0).notNull(),

  aiServiceVersion: varchar('ai_service_version', {
    length: 80,
  }),

  lastModelSyncAt: timestamp('last_model_sync_at', {
    withTimezone: true,
  }),

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

/*This is the nanoStations table*/

export const nanostations = pgTable('nanostations', {
  id: uuid('id').defaultRandom().primaryKey(),

  deviceId: uuid('device_id')
    .notNull()
    .unique()
    .references(() => devices.id, {
      onDelete: 'restrict',
      onUpdate: 'cascade',
    }),

  role: varchar('role', {
    length: 30,
  }).notNull(),

  wirelessMode: varchar('wireless_mode', {
    length: 50,
  }),

  ssid: varchar('ssid', {
    length: 120,
  }),

  frequencyMhz: integer('frequency_mhz'),

  channelWidthMhz: integer('channel_width_mhz'),

  airmaxEnabled: boolean('airmax_enabled').default(true).notNull(),

  managementUrl: text('management_url'),

  antennaGainDbi: numeric('antenna_gain_dbi', {
    precision: 5,
    scale: 2,
  }),

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

/*This is the network links table*/

export const networkLinks = pgTable('network_links', {
  id: uuid('id').defaultRandom().primaryKey(),

  linkCode: varchar('link_code', {
    length: 80,
  })
    .notNull()
    .unique(),

  name: varchar('name', {
    length: 160,
  }).notNull(),

  type: networkLinkTypeEnum('type').notNull(),

  status: networkLinkStatusEnum('status').default('offline').notNull(),

  sourceDeviceId: uuid('source_device_id')
    .notNull()
    .references(() => devices.id, {
      onDelete: 'restrict',
      onUpdate: 'cascade',
    }),

  destinationDeviceId: uuid('destination_device_id')
    .notNull()
    .references(() => devices.id, {
      onDelete: 'restrict',
      onUpdate: 'cascade',
    }),

  distanceMeters: integer('distance_meters'),

  frequencyMhz: integer('frequency_mhz'),

  channelWidthMhz: integer('channel_width_mhz'),

  expectedCapacityMbps: numeric('expected_capacity_mbps', {
    precision: 10,
    scale: 2,
  }),

  lastCheckedAt: timestamp('last_checked_at', {
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

/*This is the cameraStreams table*/

export const cameraStreams = pgTable('camera_streams', {
  id: uuid('id').defaultRandom().primaryKey(),

  cameraId: uuid('camera_id')
    .notNull()
    .references(() => cameras.id, {
      onDelete: 'cascade',
      onUpdate: 'cascade',
    }),

  name: varchar('name', {
    length: 120,
  }).notNull(),

  status: streamStatusEnum('status').default('unavailable').notNull(),

  purpose: varchar('purpose', {
    length: 50,
  }).notNull(),

  protocol: varchar('protocol', {
    length: 30,
  })
    .default('rtsp')
    .notNull(),

  streamUrl: text('stream_url'),

  resolutionWidth: integer('resolution_width'),

  resolutionHeight: integer('resolution_height'),

  framesPerSecond: integer('frames_per_second'),

  codec: varchar('codec', {
    length: 30,
  }),

  bitrateKbps: integer('bitrate_kbps'),

  isPrimary: boolean('is_primary').default(false).notNull(),

  lastAvailableAt: timestamp('last_available_at', {
    withTimezone: true,
  }),

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
| DEVICE HEARTBEATS
|--------------------------------------------------------------------------
|
| Records periodic "I am alive" messages from cameras, Jetsons,
| NanoStations, servers and other connected devices.
|--------------------------------------------------------------------------
*/

export const deviceHeartbeats = pgTable(
  'device_heartbeats',
  {
    id: uuid('id').defaultRandom().primaryKey(),

    deviceId: uuid('device_id')
      .notNull()
      .references(() => devices.id, {
        onDelete: 'cascade',
        onUpdate: 'cascade',
      }),

    status: heartbeatStatusEnum('status').default('online').notNull(),

    heartbeatAt: timestamp('heartbeat_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),

    ipAddress: varchar('ip_address', {
      length: 45,
    }),

    firmwareVersion: varchar('firmware_version', {
      length: 80,
    }),

    uptimeSeconds: integer('uptime_seconds'),

    metadata: jsonb('metadata')
      .$type<Record<string, unknown>>()
      .default({})
      .notNull(),

    createdAt: timestamp('created_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),
  },
  (table) => [
    index('device_heartbeats_device_id_idx').on(table.deviceId),

    index('device_heartbeats_heartbeat_at_idx').on(table.heartbeatAt),

    index('device_heartbeats_device_time_idx').on(
      table.deviceId,
      table.heartbeatAt,
    ),

    index('device_heartbeats_status_idx').on(table.status),
  ],
);

/*
|--------------------------------------------------------------------------
| DEVICE METRICS
|--------------------------------------------------------------------------
|
| Stores time-series numeric measurements reported by devices.
| One flexible table supports Jetsons, cameras, NanoStations, servers,
| switches and future device types without requiring new metric tables.
|--------------------------------------------------------------------------
*/

export const deviceMetrics = pgTable(
  'device_metrics',
  {
    id: uuid('id').defaultRandom().primaryKey(),

    deviceId: uuid('device_id')
      .notNull()
      .references(() => devices.id, {
        onDelete: 'cascade',
        onUpdate: 'cascade',
      }),

    metricName: varchar('metric_name', {
      length: 100,
    }).notNull(),

    metricValue: numeric('metric_value', {
      precision: 18,
      scale: 6,
    }).notNull(),

    metricUnit: varchar('metric_unit', {
      length: 30,
    }),

    recordedAt: timestamp('recorded_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),

    metadata: jsonb('metadata')
      .$type<Record<string, unknown>>()
      .default({})
      .notNull(),

    createdAt: timestamp('created_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),
  },
  (table) => [
    index('device_metrics_device_id_idx').on(table.deviceId),

    index('device_metrics_recorded_at_idx').on(table.recordedAt),

    index('device_metrics_device_time_idx').on(
      table.deviceId,
      table.recordedAt,
    ),

    index('device_metrics_device_name_time_idx').on(
      table.deviceId,
      table.metricName,
      table.recordedAt,
    ),

    index('device_metrics_metric_name_idx').on(table.metricName),
  ],
);

/*
|--------------------------------------------------------------------------
| DEVICE EVENTS
|--------------------------------------------------------------------------
|
| Stores significant operational events raised by devices or by the backend.
| Events may later trigger notifications, maintenance tasks or incidents.
|--------------------------------------------------------------------------
*/

export const deviceEvents = pgTable(
  'device_events',
  {
    id: uuid('id').defaultRandom().primaryKey(),

    deviceId: uuid('device_id')
      .notNull()
      .references(() => devices.id, {
        onDelete: 'cascade',
        onUpdate: 'cascade',
      }),

    eventType: varchar('event_type', {
      length: 100,
    }).notNull(),

    severity: eventSeverityEnum('severity').default('info').notNull(),

    title: varchar('title', {
      length: 200,
    }).notNull(),

    description: text('description'),

    occurredAt: timestamp('occurred_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),

    resolvedAt: timestamp('resolved_at', {
      withTimezone: true,
    }),

    acknowledgedAt: timestamp('acknowledged_at', {
      withTimezone: true,
    }),

    acknowledgedByUserId: uuid('acknowledged_by_user_id').references(
      () => users.id,
      {
        onDelete: 'set null',
        onUpdate: 'cascade',
      },
    ),

    metadata: jsonb('metadata')
      .$type<Record<string, unknown>>()
      .default({})
      .notNull(),

    createdAt: timestamp('created_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),
  },
  (table) => [
    index('device_events_device_id_idx').on(table.deviceId),

    index('device_events_occurred_at_idx').on(table.occurredAt),

    index('device_events_device_time_idx').on(table.deviceId, table.occurredAt),

    index('device_events_severity_idx').on(table.severity),

    index('device_events_event_type_idx').on(table.eventType),

    index('device_events_acknowledged_by_idx').on(table.acknowledgedByUserId),
  ],
);
/*
|--------------------------------------------------------------------------
| NETWORK LINK METRICS
|--------------------------------------------------------------------------
|
| Stores time-series measurements for wireless and wired network links.
| These readings will be used to monitor NanoStation connectivity,
| throughput, latency, signal quality and packet loss.
|--------------------------------------------------------------------------
*/

export const networkLinkMetrics = pgTable(
  'network_link_metrics',
  {
    id: uuid('id').defaultRandom().primaryKey(),

    networkLinkId: uuid('network_link_id')
      .notNull()
      .references(() => networkLinks.id, {
        onDelete: 'cascade',
        onUpdate: 'cascade',
      }),

    signalStrengthDbm: numeric('signal_strength_dbm', {
      precision: 6,
      scale: 2,
    }),

    noiseFloorDbm: numeric('noise_floor_dbm', {
      precision: 6,
      scale: 2,
    }),

    signalToNoiseRatioDb: numeric('signal_to_noise_ratio_db', {
      precision: 6,
      scale: 2,
    }),

    transmitCapacityMbps: numeric('transmit_capacity_mbps', {
      precision: 10,
      scale: 2,
    }),

    receiveCapacityMbps: numeric('receive_capacity_mbps', {
      precision: 10,
      scale: 2,
    }),

    transmitThroughputMbps: numeric('transmit_throughput_mbps', {
      precision: 10,
      scale: 2,
    }),

    receiveThroughputMbps: numeric('receive_throughput_mbps', {
      precision: 10,
      scale: 2,
    }),

    latencyMs: numeric('latency_ms', {
      precision: 10,
      scale: 3,
    }),

    packetLossPercent: numeric('packet_loss_percent', {
      precision: 5,
      scale: 2,
    }),

    airmaxQualityPercent: numeric('airmax_quality_percent', {
      precision: 5,
      scale: 2,
    }),

    airmaxCapacityPercent: numeric('airmax_capacity_percent', {
      precision: 5,
      scale: 2,
    }),

    connectionCount: integer('connection_count'),

    recordedAt: timestamp('recorded_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),

    metadata: jsonb('metadata')
      .$type<Record<string, unknown>>()
      .default({})
      .notNull(),

    createdAt: timestamp('created_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),
  },
  (table) => [
    index('network_link_metrics_link_id_idx').on(table.networkLinkId),

    index('network_link_metrics_recorded_at_idx').on(table.recordedAt),

    index('network_link_metrics_link_time_idx').on(
      table.networkLinkId,
      table.recordedAt,
    ),
  ],
);
/*
|--------------------------------------------------------------------------
| POWER SYSTEMS
|--------------------------------------------------------------------------
|
| Represents the complete electrical power installation serving a field
| site or control-centre installation.
|--------------------------------------------------------------------------
*/

export const powerSystems = pgTable('power_systems', {
  id: uuid('id').defaultRandom().primaryKey(),

  powerSystemCode: varchar('power_system_code', {
    length: 80,
  })
    .notNull()
    .unique(),

  name: varchar('name', {
    length: 160,
  }).notNull(),

  type: powerSystemTypeEnum('type').notNull(),

  status: powerSystemStatusEnum('status').default('planned').notNull(),

  locationId: uuid('location_id')
    .notNull()
    .references(() => locations.id, {
      onDelete: 'restrict',
      onUpdate: 'cascade',
    }),

  solarPanelAssetId: uuid('solar_panel_asset_id').references(() => assets.id, {
    onDelete: 'set null',
    onUpdate: 'cascade',
  }),

  batteryAssetId: uuid('battery_asset_id').references(() => assets.id, {
    onDelete: 'set null',
    onUpdate: 'cascade',
  }),

  chargeControllerAssetId: uuid('charge_controller_asset_id').references(
    () => assets.id,
    {
      onDelete: 'set null',
      onUpdate: 'cascade',
    },
  ),

  upsAssetId: uuid('ups_asset_id').references(() => assets.id, {
    onDelete: 'set null',
    onUpdate: 'cascade',
  }),

  nominalSystemVoltage: numeric('nominal_system_voltage', {
    precision: 6,
    scale: 2,
  }),

  solarCapacityWatts: numeric('solar_capacity_watts', {
    precision: 10,
    scale: 2,
  }),

  batteryCapacityAmpHours: numeric('battery_capacity_amp_hours', {
    precision: 10,
    scale: 2,
  }),

  maximumLoadWatts: numeric('maximum_load_watts', {
    precision: 10,
    scale: 2,
  }),

  lowBatteryThresholdPercent: numeric('low_battery_threshold_percent', {
    precision: 5,
    scale: 2,
  })
    .default('20')
    .notNull(),

  lastCheckedAt: timestamp('last_checked_at', {
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
| POWER READINGS
|--------------------------------------------------------------------------
|
| Stores time-series electrical and battery telemetry for solar, UPS,
| mains and hybrid power systems.
|--------------------------------------------------------------------------
*/

export const powerReadings = pgTable(
  'power_readings',
  {
    id: uuid('id').defaultRandom().primaryKey(),

    powerSystemId: uuid('power_system_id')
      .notNull()
      .references(() => powerSystems.id, {
        onDelete: 'cascade',
        onUpdate: 'cascade',
      }),

    solarVoltage: numeric('solar_voltage', {
      precision: 8,
      scale: 3,
    }),

    solarCurrentAmps: numeric('solar_current_amps', {
      precision: 8,
      scale: 3,
    }),

    solarPowerWatts: numeric('solar_power_watts', {
      precision: 10,
      scale: 3,
    }),

    batteryVoltage: numeric('battery_voltage', {
      precision: 8,
      scale: 3,
    }),

    batteryCurrentAmps: numeric('battery_current_amps', {
      precision: 8,
      scale: 3,
    }),

    batteryStateOfChargePercent: numeric('battery_state_of_charge_percent', {
      precision: 5,
      scale: 2,
    }),

    batteryTemperatureCelsius: numeric('battery_temperature_celsius', {
      precision: 6,
      scale: 2,
    }),

    loadVoltage: numeric('load_voltage', {
      precision: 8,
      scale: 3,
    }),

    loadCurrentAmps: numeric('load_current_amps', {
      precision: 8,
      scale: 3,
    }),

    loadPowerWatts: numeric('load_power_watts', {
      precision: 10,
      scale: 3,
    }),

    estimatedRuntimeMinutes: integer('estimated_runtime_minutes'),

    chargingState: varchar('charging_state', {
      length: 40,
    }),

    controllerTemperatureCelsius: numeric('controller_temperature_celsius', {
      precision: 6,
      scale: 2,
    }),

    recordedAt: timestamp('recorded_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),

    metadata: jsonb('metadata')
      .$type<Record<string, unknown>>()
      .default({})
      .notNull(),

    createdAt: timestamp('created_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),
  },
  (table) => [
    index('power_readings_power_system_id_idx').on(table.powerSystemId),

    index('power_readings_recorded_at_idx').on(table.recordedAt),

    index('power_readings_system_time_idx').on(
      table.powerSystemId,
      table.recordedAt,
    ),
  ],
);
/*
|--------------------------------------------------------------------------
| CAMERA STREAM METRICS
|--------------------------------------------------------------------------
|
| Stores time-series health and performance measurements for each
| individual camera stream.
|--------------------------------------------------------------------------
*/

export const cameraStreamMetrics = pgTable(
  'camera_stream_metrics',
  {
    id: uuid('id').defaultRandom().primaryKey(),

    cameraStreamId: uuid('camera_stream_id')
      .notNull()
      .references(() => cameraStreams.id, {
        onDelete: 'cascade',
        onUpdate: 'cascade',
      }),

    framesPerSecond: numeric('frames_per_second', {
      precision: 8,
      scale: 3,
    }),

    bitrateKbps: integer('bitrate_kbps'),

    latencyMs: numeric('latency_ms', {
      precision: 10,
      scale: 3,
    }),

    frameDropPercent: numeric('frame_drop_percent', {
      precision: 5,
      scale: 2,
    }),

    packetLossPercent: numeric('packet_loss_percent', {
      precision: 5,
      scale: 2,
    }),

    jitterMs: numeric('jitter_ms', {
      precision: 10,
      scale: 3,
    }),

    width: integer('width'),

    height: integer('height'),

    isReachable: boolean('is_reachable').default(false).notNull(),

    isDecoding: boolean('is_decoding').default(false).notNull(),

    lastFrameAt: timestamp('last_frame_at', {
      withTimezone: true,
    }),

    recordedAt: timestamp('recorded_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),

    metadata: jsonb('metadata')
      .$type<Record<string, unknown>>()
      .default({})
      .notNull(),

    createdAt: timestamp('created_at', {
      withTimezone: true,
    })
      .defaultNow()
      .notNull(),
  },
  (table) => [
    index('camera_stream_metrics_stream_id_idx').on(table.cameraStreamId),

    index('camera_stream_metrics_recorded_at_idx').on(table.recordedAt),

    index('camera_stream_metrics_stream_time_idx').on(
      table.cameraStreamId,
      table.recordedAt,
    ),

    index('camera_stream_metrics_reachable_idx').on(table.isReachable),
  ],
);
export type CameraStreamMetric = typeof cameraStreamMetrics.$inferSelect;

export type NewCameraStreamMetric = typeof cameraStreamMetrics.$inferInsert;

export type PowerReading = typeof powerReadings.$inferSelect;
export type NewPowerReading = typeof powerReadings.$inferInsert;

export type PowerSystem = typeof powerSystems.$inferSelect;
export type NewPowerSystem = typeof powerSystems.$inferInsert;

export type NetworkLinkMetric = typeof networkLinkMetrics.$inferSelect;
export type NewNetworkLinkMetric = typeof networkLinkMetrics.$inferInsert;

export type JetsonNode = typeof jetsonNodes.$inferSelect;
export type NewJetsonNode = typeof jetsonNodes.$inferInsert;

export type Nanostation = typeof nanostations.$inferSelect;
export type NewNanostation = typeof nanostations.$inferInsert;

export type NetworkLink = typeof networkLinks.$inferSelect;
export type NewNetworkLink = typeof networkLinks.$inferInsert;

export type CameraStream = typeof cameraStreams.$inferSelect;
export type NewCameraStream = typeof cameraStreams.$inferInsert;

export type DeviceHeartbeat = typeof deviceHeartbeats.$inferSelect;
export type NewDeviceHeartbeat = typeof deviceHeartbeats.$inferInsert;

export type DeviceMetric = typeof deviceMetrics.$inferSelect;
export type NewDeviceMetric = typeof deviceMetrics.$inferInsert;

export type DeviceEvent = typeof deviceEvents.$inferSelect;
export type NewDeviceEvent = typeof deviceEvents.$inferInsert;
