import 'dotenv/config';
import { drizzle } from 'drizzle-orm/postgres-js';
import { migrate } from 'drizzle-orm/postgres-js/migrator';
import postgres from 'postgres';

async function runMigrations(): Promise<void> {
  const connectionString = process.env.DATABASE_URL;

  if (!connectionString) {
    throw new Error('DATABASE_URL is not defined');
  }

  const client = postgres(connectionString, {
    max: 1,
    onnotice: () => {
      // Suppress harmless PostgreSQL NOTICE messages.
    },
  });

  const database = drizzle(client);

  try {
    console.log('Applying database migrations...');

    await migrate(database, {
      migrationsFolder: './drizzle',
    });

    console.log('All migrations applied successfully.');
  } catch (error: unknown) {
    console.error('Migration failed with the following error:');
    console.error(error);

    if (error instanceof Error && error.cause) {
      console.error('Underlying cause:');
      console.error(error.cause);
    }

    process.exitCode = 1;
  } finally {
    await client.end();
  }
}

void runMigrations();
