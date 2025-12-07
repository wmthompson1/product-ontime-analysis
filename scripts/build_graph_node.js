#!/usr/bin/env node
/**
 * Graph Builder using Graphology (Node.js)
 * 
 * This script builds a supply chain graph from the product on-time analysis database.
 * It creates nodes for suppliers, parts, and products, with edges representing relationships.
 * 
 * Usage:
 *   node scripts/build_graph_node.js [options]
 * 
 * Options:
 *   --output <file>    Output file path (default: graph_output.json)
 *   --format <type>    Output format: json, gexf, graphml (default: json)
 *   --analyze          Run graph analytics (centrality, communities, etc.)
 */

const { Client } = require('pg');
const fs = require('fs').promises;
const path = require('path');

// Check if graphology is available
let Graph, centrality;
try {
  Graph = require('graphology');
  centrality = require('graphology-metrics/centrality');
  console.log('✅ Graphology library loaded');
} catch (error) {
  console.error('❌ Graphology not found. Install with: npm install graphology graphology-metrics');
  process.exit(1);
}

// Configuration
const DB_CONFIG = {
  host: process.env.PGHOST || 'localhost',
  port: process.env.PGPORT || 5432,
  database: process.env.PGDATABASE || 'product_ontime',
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD || 'postgres',
};

// Parse command line arguments
const args = process.argv.slice(2);
let outputFile = 'graph_output.json';
let outputFormat = 'json';
let shouldAnalyze = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--output' && i + 1 < args.length) {
    outputFile = args[i + 1];
    i++;
  } else if (args[i] === '--format' && i + 1 < args.length) {
    outputFormat = args[i + 1];
    i++;
  } else if (args[i] === '--analyze') {
    shouldAnalyze = true;
  }
}

/**
 * Build supply chain graph from database
 */
async function buildSupplyChainGraph(client) {
  console.log('\n🔨 Building supply chain graph...');
  
  const graph = new Graph({ type: 'directed', multi: false });

  // Add supplier nodes
  console.log('  📦 Adding supplier nodes...');
  const suppliersResult = await client.query(`
    SELECT supplier_id, supplier_name, supplier_code, country
    FROM suppliers
    ORDER BY supplier_id
  `);
  
  suppliersResult.rows.forEach(supplier => {
    graph.addNode(`supplier_${supplier.supplier_id}`, {
      type: 'supplier',
      name: supplier.supplier_name,
      code: supplier.supplier_code,
      country: supplier.country,
      label: supplier.supplier_name
    });
  });
  console.log(`  ✅ Added ${suppliersResult.rows.length} supplier nodes`);

  // Add part nodes
  console.log('  🔩 Adding part nodes...');
  const partsResult = await client.query(`
    SELECT p.part_id, p.part_number, p.part_name, p.supplier_id, p.unit_cost, p.lead_time_days
    FROM parts p
    ORDER BY p.part_id
  `);
  
  partsResult.rows.forEach(part => {
    graph.addNode(`part_${part.part_id}`, {
      type: 'part',
      number: part.part_number,
      name: part.part_name,
      cost: part.unit_cost,
      lead_time: part.lead_time_days,
      label: part.part_name
    });
    
    // Add edge from supplier to part
    if (part.supplier_id) {
      graph.addEdge(
        `supplier_${part.supplier_id}`,
        `part_${part.part_id}`,
        {
          type: 'supplies',
          cost: part.unit_cost,
          lead_time: part.lead_time_days
        }
      );
    }
  });
  console.log(`  ✅ Added ${partsResult.rows.length} part nodes`);

  // Add product nodes
  console.log('  📦 Adding product nodes...');
  const productsResult = await client.query(`
    SELECT product_id, product_code, product_name, product_family, target_cycle_time_hours
    FROM products
    ORDER BY product_id
  `);
  
  productsResult.rows.forEach(product => {
    graph.addNode(`product_${product.product_id}`, {
      type: 'product',
      code: product.product_code,
      name: product.product_name,
      family: product.product_family,
      cycle_time: product.target_cycle_time_hours,
      label: product.product_name
    });
  });
  console.log(`  ✅ Added ${productsResult.rows.length} product nodes`);

  // Add assembly edges (part -> product)
  console.log('  🔗 Adding assembly relationships...');
  const assembliesResult = await client.query(`
    SELECT product_id, part_id, quantity_required
    FROM assemblies
    ORDER BY product_id, part_id
  `);
  
  assembliesResult.rows.forEach(assembly => {
    graph.addEdge(
      `part_${assembly.part_id}`,
      `product_${assembly.product_id}`,
      {
        type: 'used_in',
        quantity: assembly.quantity_required
      }
    );
  });
  console.log(`  ✅ Added ${assembliesResult.rows.length} assembly relationships`);

  return graph;
}

/**
 * Analyze graph metrics
 */
function analyzeGraph(graph) {
  console.log('\n📊 Graph Analysis:');
  console.log(`  Nodes: ${graph.order}`);
  console.log(`  Edges: ${graph.size}`);
  
  // Calculate density, handling edge case where graph has fewer than 2 nodes
  const density = graph.order >= 2 
    ? (graph.size / (graph.order * (graph.order - 1))).toFixed(4)
    : '0.0000';
  console.log(`  Density: ${density}`);
  
  // Count by node type
  const nodeTypes = {};
  graph.forEachNode((node, attrs) => {
    nodeTypes[attrs.type] = (nodeTypes[attrs.type] || 0) + 1;
  });
  console.log('\n  Node types:');
  Object.entries(nodeTypes).forEach(([type, count]) => {
    console.log(`    ${type}: ${count}`);
  });

  // Calculate degree centrality
  console.log('\n  🎯 Calculating centrality metrics...');
  try {
    const degreeCentrality = centrality.degree(graph);
    
    // Find top nodes by degree
    const topNodes = Object.entries(degreeCentrality)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    
    console.log('  Top 5 most connected nodes:');
    topNodes.forEach(([nodeId, degree]) => {
      const attrs = graph.getNodeAttributes(nodeId);
      console.log(`    ${attrs.label} (${attrs.type}): ${degree} connections`);
    });
  } catch (error) {
    console.log('  ⚠️  Centrality calculation skipped:', error.message);
  }
}

/**
 * Export graph to JSON
 */
function exportToJson(graph) {
  const data = {
    nodes: [],
    edges: []
  };

  graph.forEachNode((node, attrs) => {
    data.nodes.push({
      id: node,
      ...attrs
    });
  });

  graph.forEachEdge((edge, attrs, source, target) => {
    data.edges.push({
      id: edge,
      source,
      target,
      ...attrs
    });
  });

  return JSON.stringify(data, null, 2);
}

/**
 * Main function
 */
async function main() {
  console.log('🚀 Supply Chain Graph Builder (Graphology)\n');
  console.log('Database configuration:');
  console.log(`   Host: ${DB_CONFIG.host}`);
  console.log(`   Port: ${DB_CONFIG.port}`);
  console.log(`   Database: ${DB_CONFIG.database}`);

  const client = new Client(DB_CONFIG);

  try {
    // Connect to database
    console.log('\n🔌 Connecting to database...');
    await client.connect();
    console.log('✅ Connected to database');

    // Build graph
    const graph = await buildSupplyChainGraph(client);

    // Analyze if requested
    if (shouldAnalyze) {
      analyzeGraph(graph);
    }

    // Export graph
    console.log(`\n💾 Exporting graph to ${outputFile}...`);
    const graphData = exportToJson(graph);
    await fs.writeFile(outputFile, graphData, 'utf-8');
    console.log(`✅ Graph exported successfully`);
    console.log(`   File: ${path.resolve(outputFile)}`);
    console.log(`   Size: ${(graphData.length / 1024).toFixed(2)} KB`);

    console.log('\n✨ Graph building completed successfully!');

  } catch (error) {
    console.error('\n❌ Error:', error.message);
    process.exit(1);
  } finally {
    await client.end();
    console.log('🔌 Database connection closed');
  }
}

// Run the script
main().catch(error => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
