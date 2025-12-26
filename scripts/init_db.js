#!/usr/bin/env node
/**
 * Database Initialization Script
 * 
 * This script initializes an embedded PostgreSQL database for local development.
 * It sets up the schema and optionally loads sample data.
 * 
 * Usage:
 *   node scripts/init_db.js [--sample-data]
 * 
 * Options:
 *   --sample-data    Load sample data after creating schema
 *   --drop-existing  Drop and recreate all tables (WARNING: data loss)
 */

const fs = require('fs').promises;
const path = require('path');
const { Client } = require('pg');

// Configuration
const DB_CONFIG = {
  host: process.env.PGHOST || 'localhost',
  port: process.env.PGPORT || 5432,
  database: process.env.PGDATABASE || 'product_ontime',
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD || 'postgres',
};

const SCHEMA_FILE = path.join(__dirname, '..', 'sql', 'schema.sql');
const SAMPLE_DATA_FILE = path.join(__dirname, '..', 'sql', 'sample_data.sql');

// Parse command line arguments
const args = process.argv.slice(2);
const shouldLoadSampleData = args.includes('--sample-data');
const shouldDropExisting = args.includes('--drop-existing');

/**
 * Execute a SQL file
 */
async function executeSqlFile(client, filePath, description) {
  console.log(`\n📄 Executing ${description}...`);
  try {
    const sql = await fs.readFile(filePath, 'utf-8');
    await client.query(sql);
    console.log(`✅ ${description} completed successfully`);
    return true;
  } catch (error) {
    console.error(`❌ Error executing ${description}:`, error.message);
    return false;
  }
}

/**
 * Drop all tables (if requested)
 */
async function dropTables(client) {
  console.log('\n🗑️  Dropping existing tables...');
  const dropSql = `
    DROP TABLE IF EXISTS quality_metrics CASCADE;
    DROP TABLE IF EXISTS production_runs CASCADE;
    DROP TABLE IF EXISTS deliveries CASCADE;
    DROP TABLE IF EXISTS assemblies CASCADE;
    DROP TABLE IF EXISTS products CASCADE;
    DROP TABLE IF EXISTS parts CASCADE;
    DROP TABLE IF EXISTS suppliers CASCADE;
    DROP VIEW IF EXISTS supplier_performance CASCADE;
    DROP VIEW IF EXISTS product_quality CASCADE;
    DROP VIEW IF EXISTS daily_delivery_summary CASCADE;
  `;
  
  try {
    await client.query(dropSql);
    console.log('✅ Existing tables dropped');
    return true;
  } catch (error) {
    console.error('❌ Error dropping tables:', error.message);
    return false;
  }
}

/**
 * Verify database connectivity
 */
async function verifyConnection(client) {
  try {
    const result = await client.query('SELECT version()');
    console.log('✅ Database connection established');
    console.log(`   PostgreSQL version: ${result.rows[0].version.split(',')[0]}`);
    return true;
  } catch (error) {
    console.error('❌ Database connection failed:', error.message);
    return false;
  }
}

/**
 * Main initialization function
 */
async function initializeDatabase() {
  console.log('🚀 Product On-Time Analysis - Database Initialization\n');
  console.log('Database configuration:');
  console.log(`   Host: ${DB_CONFIG.host}`);
  console.log(`   Port: ${DB_CONFIG.port}`);
  console.log(`   Database: ${DB_CONFIG.database}`);
  console.log(`   User: ${DB_CONFIG.user}`);

  const client = new Client(DB_CONFIG);

  try {
    // Connect to database
    console.log('\n🔌 Connecting to database...');
    await client.connect();
    
    // Verify connection
    const connected = await verifyConnection(client);
    if (!connected) {
      process.exit(1);
    }

    // Drop existing tables if requested
    if (shouldDropExisting) {
      const dropped = await dropTables(client);
      if (!dropped) {
        console.warn('⚠️  Failed to drop existing tables, continuing anyway...');
      }
    }

    // Create schema
    const schemaCreated = await executeSqlFile(client, SCHEMA_FILE, 'schema creation');
    if (!schemaCreated) {
      console.error('\n❌ Schema creation failed. Aborting.');
      process.exit(1);
    }

    // Load sample data if requested
    if (shouldLoadSampleData) {
      const dataLoaded = await executeSqlFile(client, SAMPLE_DATA_FILE, 'sample data loading');
      if (!dataLoaded) {
        console.warn('\n⚠️  Sample data loading failed, but schema was created successfully.');
      }
    }

    // Verify tables were created
    console.log('\n🔍 Verifying database setup...');
    const tableCheck = await client.query(`
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
      ORDER BY table_name
    `);
    
    console.log(`✅ Found ${tableCheck.rows.length} tables:`);
    tableCheck.rows.forEach(row => {
      console.log(`   - ${row.table_name}`);
    });

    // Verify views were created
    const viewCheck = await client.query(`
      SELECT table_name 
      FROM information_schema.views 
      WHERE table_schema = 'public'
      ORDER BY table_name
    `);
    
    if (viewCheck.rows.length > 0) {
      console.log(`\n✅ Found ${viewCheck.rows.length} views:`);
      viewCheck.rows.forEach(row => {
        console.log(`   - ${row.table_name}`);
      });
    }

    console.log('\n✨ Database initialization completed successfully!');
    
    if (!shouldLoadSampleData) {
      console.log('\n💡 Tip: Run with --sample-data flag to load sample data:');
      console.log('   node scripts/init_db.js --sample-data');
    }

  } catch (error) {
    console.error('\n❌ Fatal error:', error.message);
    process.exit(1);
  } finally {
    await client.end();
    console.log('\n🔌 Database connection closed');
  }
}

// Run the initialization
initializeDatabase().catch(error => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
