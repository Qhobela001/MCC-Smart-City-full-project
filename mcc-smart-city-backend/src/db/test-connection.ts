import 'dotenv/config';
import postgres from 'postgres';

async function testConnection(): Promise<void> {
  const connectionString = process.env.DATABASE_URL;

  if (!connectionString) {
    throw new Error('DATABASE_URL is not defined');
  }

  const sql = postgres(connectionString);

  try {
    const result = await sql`
      select current_database() as database_name,
             current_user as database_user,
             now() as server_time
    `;

    console.log('Database connection successful:');
    console.table(result);
  } catch (error) {
    console.error('Database connection failed:', error);
    process.exitCode = 1;
  } finally {
    await sql.end();
  }
}

void testConnection();
