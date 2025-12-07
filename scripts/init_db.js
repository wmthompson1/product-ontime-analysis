#!/usr/bin/env node

/**
 * init_db.js: Initialize embedded Postgres with embedded-postgres, apply schema and sample data
 * Environment: KEEP_PG=1 to keep Postgres running after initialization
 */

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');
const EmbeddedPostgres = require('embedded-postgres').default;
require('dotenv').config();

const SCHEMA_FILE = path.join(__dirname, '..', 'sql', 'schema.sql');
const SAMPLE_DATA_FILE = path.join(__dirname, '..', 'sql', 'sample_data.sql');
const DB_NAME = 'pta_dev';
const KEEP_PG = process.env.KEEP_PG === '1';

async function main() {
  console.log('🚀 Starting embedded Postgres...');
  
  const pg = new EmbeddedPostgres({
    databaseDir: path.join(__dirname, '..', '.pgdata'),
    user: 'postgres',
    password: 'postgres',
    port: 5432,
    persistent: true,
  });

  try {
    await pg.initialise();
    await pg.start();
    console.log('✅ Postgres started');

    // Create database
    console.log(`📊 Creating database ${DB_NAME}...`);
    try {
      await pg.createDatabase(DB_NAME);
      console.log(`✅ Database ${DB_NAME} created`);
    } catch (error) {
      if (error.message && error.message.includes('already exists')) {
        console.log(`✅ Database ${DB_NAME} already exists`);
      } else {
        throw error;
      }
    }

    // Connect to the new database and apply schema
    const client = new Client({
      user: 'postgres',
      password: 'postgres',
      host: 'localhost',
      port: 5432,
      database: DB_NAME,
    });

    await client.connect();
    console.log(`📝 Applying schema from ${SCHEMA_FILE}...`);
    const schema = fs.readFileSync(SCHEMA_FILE, 'utf8');
    await client.query(schema);
    console.log('✅ Schema applied');

    console.log(`📝 Inserting sample data from ${SAMPLE_DATA_FILE}...`);
    const sampleData = fs.readFileSync(SAMPLE_DATA_FILE, 'utf8');
    await client.query(sampleData);
    console.log('✅ Sample data inserted');

    await client.end();

    if (KEEP_PG) {
      console.log('');
      console.log('🎉 Database initialized successfully!');
      console.log('📌 Postgres is still running (KEEP_PG=1)');
      console.log('');
      console.log('Connection string:');
      console.log(`  postgresql://postgres:postgres@localhost:5432/${DB_NAME}`);
      console.log('');
      console.log('To stop Postgres, kill this process or use Ctrl+C');
      console.log('');
      
      // Keep process alive
      await new Promise(() => {});
    } else {
      console.log('🛑 Stopping embedded Postgres...');
      await pg.stop();
      console.log('✅ Postgres stopped');
      console.log('');
      console.log('🎉 Database initialized successfully!');
      console.log('');
      console.log('To keep Postgres running, use:');
      console.log('  npm run init-db-keep');
    }

  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  }
}

main();
