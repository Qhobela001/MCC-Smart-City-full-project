export interface DbConfig {
  host: string;
  port: number;
  user: string;
  password: string;
  database: string;
}

export interface AppConfig {
  port: number;
  apiPrefix: string;
  corsOrigins: string[];
  db: DbConfig;
}

export function getAppConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const corsOrigins = (env.CORS_ORIGINS ?? 'http://localhost:3000')
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean);

  const dbHost = env.DB_HOST ?? 'db';
  const dbPort = Number(env.DB_PORT ?? 5432);
  const dbUser = env.DB_USER ?? 'postgres';
  const dbPassword = env.DB_PASSWORD ?? 'postgres';
  const dbName = env.DB_NAME ?? 'mcc_smart_city';

  return {
    port: Number(env.PORT ?? 4000),
    apiPrefix: env.API_PREFIX ?? 'api',
    corsOrigins,
    db: {
      host: dbHost,
      port: dbPort,
      user: dbUser,
      password: dbPassword,
      database: dbName,
    },
  };
}
