import knex from 'knex';
import logger from './utils/logger';

const db = knex({
  client: 'pg',
  connection: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
    database: process.env.DB_NAME || 'rpm_dev',
  },
  migrations: {
    directory: './migrations',
  },
  seeds: {
    directory: './seeds',
  },
});

export const setupDatabase = async () => {
  try {
    // Test connection
    await db.raw('SELECT 1');
    logger.info('Database connection successful');

    // Run migrations
    await db.migrate.latest();
    logger.info('Migrations completed');
  } catch (error) {
    logger.error('Database setup failed:', error);
    throw error;
  }
};

export default db;
