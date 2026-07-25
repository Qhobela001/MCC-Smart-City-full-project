export interface AppConfig {
  port: number;
  apiPrefix: string;
  corsOrigins: string[];
}

export function getAppConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  const corsOrigins = (env.CORS_ORIGINS ?? 'http://localhost:3000')
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean);

  return {
    port: Number(env.PORT ?? 4000),
    apiPrefix: env.API_PREFIX ?? 'api',
    corsOrigins,
  };
}
