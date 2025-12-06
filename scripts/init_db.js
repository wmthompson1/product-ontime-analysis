#!/usr/bin/env node

/**
 * init_db.js: Initialize embedded Postgres with pg-embed, apply schema and sample data
 * Environment: KEEP_PG=1 to keep Postgres running after initialization
 */

const fs = require('fs');
const path = require('path');
const { Client } = require('pg');
const PgEmbed = require('pg-embed');
require('dotenv').config();

const SCHEMA_FILE = path.join(__dirname, '..', 'sql', 'schema.sql');
const SAMPLE_DATA_FILE = path.join(__dirname, '..', 'sql', 'sample_data.sql');
const DB_NAME = 'pta_dev';
const KEEP_PG = process.env.KEEP_PG === '1';

async function main() {
  console.log('🚀 Starting embedded Postgres with pg-embed...');
  
  const pgEmbed = new PgEmbed({
    databaseDir: path.join(__dirname, '..', '.pgdata'),
    user: 'postgres',
    password: 'postgres',
    port: 5432,
    persistent: KEEP_PG,
  });

  try {
    await pgEmbed.start();
    console.log('✅ Postgres started');

    // Create database
    const adminClient = new Client({
      user: 'postgres',
      password: 'postgres',
      host: 'localhost',
      port: 5432,
      database: 'postgres',
    });

    await adminClient.connect();
    console.log(`📊 Creating database ${DB_NAME}...`);
    
    // Check if database exists
    const dbCheckResult = await adminClient.query(
      `SELECT 1 FROM pg_database WHERE datname = $1`,
      [DB_NAME]
    );
    
    if (dbCheckResult.rows.length === 0) {
      await adminClient.query(`CREATE DATABASE ${DB_NAME}`);
      console.log(`✅ Database ${DB_NAME} created`);
    } else {
      console.log(`✅ Database ${DB_NAME} already exists`);
    }
    
    await adminClient.end();

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
      console.log('To stop Postgres, kill this process or run:');
      console.log('  pkill -f postgres');
    } else {
      console.log('🛑 Stopping embedded Postgres...');
      await pgEmbed.stop();
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
