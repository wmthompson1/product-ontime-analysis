#!/usr/bin/env node

/**
 * build_graph_node.js: Build a supply chain graph using graphology (Node.js)
 * Reads from Postgres and creates a graph with suppliers -> parts -> assemblies -> products
 */

const { Client } = require('pg');
const Graph = require('graphology');
const { createObjectCsvWriter } = require('csv-writer');
const path = require('path');
require('dotenv').config();

const DB_NAME = process.env.DB_NAME || 'pta_dev';
const DB_USER = process.env.DB_USER || 'postgres';
const DB_PASSWORD = process.env.DB_PASSWORD || 'postgres';
const DB_HOST = process.env.DB_HOST || 'localhost';
const DB_PORT = process.env.DB_PORT || 5432;

async function buildGraph() {
  console.log('🔨 Building supply chain graph with graphology...');

  const client = new Client({
    user: DB_USER,
    password: DB_PASSWORD,
    host: DB_HOST,
    port: DB_PORT,
    database: DB_NAME,
  });

  await client.connect();

  const graph = new Graph({ multi: false, type: 'directed' });

  // Fetch suppliers
  console.log('📦 Adding suppliers...');
  const suppliers = await client.query('SELECT * FROM pta.suppliers');
  for (const row of suppliers.rows) {
    graph.addNode(`supplier_${row.supplier_id}`, {
      type: 'supplier',
      name: row.name,
      country: row.country,
    });
  }

  // Fetch parts and link to suppliers
  console.log('🔩 Adding parts...');
  const parts = await client.query('SELECT * FROM pta.parts');
  for (const row of parts.rows) {
    const unitCost = row.unit_cost !== null ? parseFloat(row.unit_cost) : null;
    if (unitCost === null) {
      console.warn(`Warning: Part ${row.part_id} has null unit_cost`);
    }
    graph.addNode(`part_${row.part_id}`, {
      type: 'part',
      part_number: row.part_number,
      description: row.description,
      unit_cost: unitCost || 0,
    });
    if (row.supplier_id) {
      graph.addEdge(
        `supplier_${row.supplier_id}`,
        `part_${row.part_id}`,
        { relationship: 'supplies' }
      );
    }
  }

  // Fetch assemblies
  console.log('🔧 Adding assemblies...');
  const assemblies = await client.query('SELECT * FROM pta.assemblies');
  for (const row of assemblies.rows) {
    graph.addNode(`assembly_${row.assembly_id}`, {
      type: 'assembly',
      assembly_code: row.assembly_code,
      description: row.description,
    });
  }

  // Link parts to assemblies
  console.log('🔗 Linking parts to assemblies...');
  const assemblyParts = await client.query('SELECT * FROM pta.assembly_parts');
  for (const row of assemblyParts.rows) {
    graph.addEdge(
      `part_${row.part_id}`,
      `assembly_${row.assembly_id}`,
      { relationship: 'used_in', qty: row.qty }
    );
  }

  // Fetch products
  console.log('📦 Adding products...');
  const products = await client.query('SELECT * FROM pta.products');
  for (const row of products.rows) {
    const listPrice = row.list_price !== null ? parseFloat(row.list_price) : null;
    if (listPrice === null) {
      console.warn(`Warning: Product ${row.product_id} has null list_price`);
    }
    graph.addNode(`product_${row.product_id}`, {
      type: 'product',
      sku: row.sku,
      name: row.name,
      list_price: listPrice || 0,
    });
    if (row.assembly_id) {
      graph.addEdge(
        `assembly_${row.assembly_id}`,
        `product_${row.product_id}`,
        { relationship: 'assembled_into' }
      );
    }
  }

  await client.end();

  // Display graph stats
  console.log('');
  console.log('📊 Graph Statistics:');
  console.log(`  Nodes: ${graph.order}`);
  console.log(`  Edges: ${graph.size}`);
  console.log('');

  // Export nodes to CSV
  const nodesOutputPath = path.join(__dirname, '..', 'graph_nodes.csv');
  const nodesCsvWriter = createObjectCsvWriter({
    path: nodesOutputPath,
    header: [
      { id: 'id', title: 'NODE_ID' },
      { id: 'type', title: 'TYPE' },
      { id: 'label', title: 'LABEL' },
      { id: 'data', title: 'DATA_JSON' },
    ],
  });

  const nodeRecords = [];
  graph.forEachNode((node, attributes) => {
    nodeRecords.push({
      id: node,
      type: attributes.type || 'unknown',
      label: attributes.name || attributes.part_number || attributes.assembly_code || attributes.sku || node,
      data: JSON.stringify(attributes),
    });
  });

  await nodesCsvWriter.writeRecords(nodeRecords);
  console.log(`✅ Nodes exported to ${nodesOutputPath}`);

  // Export edges to CSV
  const edgesOutputPath = path.join(__dirname, '..', 'graph_edges.csv');
  const edgesCsvWriter = createObjectCsvWriter({
    path: edgesOutputPath,
    header: [
      { id: 'source', title: 'SOURCE' },
      { id: 'target', title: 'TARGET' },
      { id: 'relationship', title: 'RELATIONSHIP' },
      { id: 'data', title: 'DATA_JSON' },
    ],
  });

  const edgeRecords = [];
  graph.forEachEdge((edge, attributes, source, target) => {
    edgeRecords.push({
      source,
      target,
      relationship: attributes.relationship || 'related',
      data: JSON.stringify(attributes),
    });
  });

  await edgesCsvWriter.writeRecords(edgeRecords);
  console.log(`✅ Edges exported to ${edgesOutputPath}`);

  console.log('');
  console.log('🎉 Graph built successfully!');
  console.log('');
  console.log('To visualize or analyze further, you can:');
  console.log('  - Import the CSV files into a graph tool');
  console.log('  - Use the optional Python NetworkX exporter: python scripts/networkx_build.py');
}

buildGraph().catch((err) => {
  console.error('❌ Error building graph:', err);
  process.exit(1);
});
