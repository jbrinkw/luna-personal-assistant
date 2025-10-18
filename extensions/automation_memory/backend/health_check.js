#!/usr/bin/env node
/**
 * Health Check Script for Automation Memory
 * Validates all components the UI relies on to determine connection status
 */

const path = require('path');
const { Pool } = require('pg');

// Load environment from project root
require('dotenv').config({ path: path.resolve(__dirname, '../../../.env') });

const API_BASE = 'http://127.0.0.1:3051';
const AM_API_PORT = process.env.AM_API_PORT || 3051;

// Color codes for output
const RED = '\x1b[31m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[36m';
const RESET = '\x1b[0m';

let hasErrors = false;
let hasWarnings = false;

function log(message, color = RESET) {
  console.log(`${color}${message}${RESET}`);
}

function success(message) {
  log(`✓ ${message}`, GREEN);
}

function error(message) {
  log(`✗ ${message}`, RED);
  hasErrors = true;
}

function warning(message) {
  log(`⚠ ${message}`, YELLOW);
  hasWarnings = true;
}

function info(message) {
  log(`ℹ ${message}`, BLUE);
}

// Test 1: Check environment variables
async function checkEnvironment() {
  info('\n[1] Checking Environment Variables');
  
  const dbHost = process.env.DB_HOST || process.env.PGHOST || '127.0.0.1';
  const dbPort = process.env.DB_PORT || process.env.PGPORT || '5432';
  const dbName = process.env.DB_NAME || process.env.PGDATABASE || 'luna';
  const dbUser = process.env.DB_USER || process.env.PGUSER || 'postgres';
  const dbPassword = process.env.DB_PASSWORD || process.env.PGPASSWORD;
  
  if (!dbPassword) {
    warning('DB_PASSWORD not set in .env');
  } else {
    success('DB_PASSWORD is set');
  }
  
  info(`  Database: ${dbUser}@${dbHost}:${dbPort}/${dbName}`);
  
  return { dbHost, dbPort, dbName, dbUser, dbPassword };
}

// Test 2: Check database connectivity
async function checkDatabaseConnection(dbConfig) {
  info('\n[2] Checking Database Connection');
  
  const pool = new Pool({
    host: dbConfig.dbHost,
    port: Number(dbConfig.dbPort),
    database: dbConfig.dbName,
    user: dbConfig.dbUser,
    password: dbConfig.dbPassword,
    connectionTimeoutMillis: 5000,
  });
  
  try {
    const client = await pool.connect();
    success(`Connected to PostgreSQL at ${dbConfig.dbHost}:${dbConfig.dbPort}`);
    client.release();
    return pool;
  } catch (e) {
    error(`Cannot connect to database: ${e.message}`);
    error(`  → UI will show: Disconnected`);
    return null;
  }
}

// Test 3: Check database tables
async function checkDatabaseTables(pool) {
  info('\n[3] Checking Database Tables');
  
  if (!pool) {
    error('Skipping table checks (no database connection)');
    return false;
  }
  
  const requiredTables = ['memories', 'task_flows', 'scheduled_prompts'];
  let allTablesExist = true;
  
  for (const table of requiredTables) {
    try {
      const result = await pool.query(
        `SELECT EXISTS (
          SELECT FROM information_schema.tables 
          WHERE table_schema = 'public' 
          AND table_name = $1
        );`,
        [table]
      );
      
      if (result.rows[0].exists) {
        success(`Table '${table}' exists`);
      } else {
        error(`Table '${table}' does NOT exist`);
        allTablesExist = false;
      }
    } catch (e) {
      error(`Error checking table '${table}': ${e.message}`);
      allTablesExist = false;
    }
  }
  
  return allTablesExist;
}

// Test 4: Test database queries
async function testDatabaseQueries(pool) {
  info('\n[4] Testing Database Queries');
  
  if (!pool) {
    error('Skipping query tests (no database connection)');
    return false;
  }
  
  const queries = [
    { name: 'memories', sql: 'SELECT id, content FROM memories LIMIT 1' },
    { name: 'task_flows', sql: 'SELECT id, call_name, prompts, agent FROM task_flows LIMIT 1' },
    { name: 'scheduled_prompts', sql: 'SELECT id, time_of_day, days_of_week, prompt, agent, enabled FROM scheduled_prompts LIMIT 1' },
  ];
  
  let allQueriesWork = true;
  
  for (const query of queries) {
    try {
      const result = await pool.query(query.sql);
      success(`Query '${query.name}' succeeded (${result.rows.length} rows)`);
    } catch (e) {
      error(`Query '${query.name}' failed: ${e.message}`);
      allQueriesWork = false;
    }
  }
  
  return allQueriesWork;
}

// Test 5: Check if backend server is running
async function checkBackendServer() {
  info('\n[5] Checking Backend Server (Port ' + AM_API_PORT + ')');
  
  try {
    // Check if process is listening on the port
    const { exec } = require('child_process');
    const { promisify } = require('util');
    const execAsync = promisify(exec);
    
    const { stdout } = await execAsync(`lsof -i :${AM_API_PORT} -P -n 2>/dev/null | grep LISTEN || echo ""`);
    
    if (stdout.trim()) {
      success(`Backend server is running on port ${AM_API_PORT}`);
      return true;
    } else {
      error(`No process listening on port ${AM_API_PORT}`);
      error(`  → UI will show: Disconnected`);
      return false;
    }
  } catch (e) {
    warning(`Could not check port status: ${e.message}`);
    return false;
  }
}

// Test 6: Test API /healthz endpoint (EXACTLY what UI checks)
async function testHealthzEndpoint() {
  info('\n[6] Testing API /healthz Endpoint (UI Health Check)');
  
  try {
    const response = await fetch(`${API_BASE}/healthz`);
    const data = await response.json();
    
    if (data.status === 'ok') {
      success(`/healthz returned status: ok`);
      success(`  → UI will show: Connected`);
      return true;
    } else {
      error(`/healthz returned unexpected status: ${data.status}`);
      error(`  → UI will show: Error`);
      return false;
    }
  } catch (e) {
    error(`Cannot reach /healthz endpoint: ${e.message}`);
    error(`  → UI will show: Disconnected`);
    return false;
  }
}

// Test 7: Test API data endpoints
async function testAPIEndpoints() {
  info('\n[7] Testing API Data Endpoints');
  
  const endpoints = [
    { path: '/api/memories', name: 'Memories' },
    { path: '/api/task_flows', name: 'Task Flows' },
    { path: '/api/scheduled_prompts', name: 'Scheduled Prompts' },
    { path: '/api/agents', name: 'Agents' },
  ];
  
  let allEndpointsWork = true;
  
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(`${API_BASE}${endpoint.path}`);
      const data = await response.json();
      
      if (response.ok) {
        const count = Array.isArray(data) ? data.length : (data.agents ? data.agents.length : 'N/A');
        success(`${endpoint.name}: ${count} items`);
      } else {
        error(`${endpoint.name}: HTTP ${response.status}`);
        allEndpointsWork = false;
      }
    } catch (e) {
      error(`${endpoint.name}: ${e.message}`);
      allEndpointsWork = false;
    }
  }
  
  return allEndpointsWork;
}

// Test 8: Check CORS configuration
async function testCORS() {
  info('\n[8] Testing CORS Configuration');
  
  try {
    const response = await fetch(`${API_BASE}/healthz`, {
      method: 'OPTIONS',
      headers: {
        'Origin': 'http://127.0.0.1:5200',
        'Access-Control-Request-Method': 'GET',
      },
    });
    
    const corsHeader = response.headers.get('Access-Control-Allow-Origin');
    if (corsHeader === '*' || corsHeader === 'http://127.0.0.1:5200') {
      success('CORS is properly configured');
      return true;
    } else {
      warning(`CORS header: ${corsHeader || 'not set'}`);
      return false;
    }
  } catch (e) {
    warning(`Could not test CORS: ${e.message}`);
    return false;
  }
}

// Main execution
async function main() {
  log('\n' + '='.repeat(60), BLUE);
  log('  AUTOMATION MEMORY HEALTH CHECK', BLUE);
  log('='.repeat(60) + '\n', BLUE);
  
  const dbConfig = await checkEnvironment();
  const pool = await checkDatabaseConnection(dbConfig);
  
  if (pool) {
    await checkDatabaseTables(pool);
    await testDatabaseQueries(pool);
  }
  
  const serverRunning = await checkBackendServer();
  
  if (serverRunning) {
    const healthzOk = await testHealthzEndpoint();
    
    if (healthzOk) {
      await testAPIEndpoints();
      await testCORS();
    }
  }
  
  // Close pool
  if (pool) {
    await pool.end();
  }
  
  // Final summary
  log('\n' + '='.repeat(60), BLUE);
  log('  SUMMARY', BLUE);
  log('='.repeat(60), BLUE);
  
  if (hasErrors) {
    log('\n❌ HEALTH CHECK FAILED', RED);
    log('The UI will show status as: DISCONNECTED or ERROR', RED);
    process.exit(1);
  } else if (hasWarnings) {
    log('\n⚠️  HEALTH CHECK PASSED WITH WARNINGS', YELLOW);
    log('The UI should show status as: Connected', YELLOW);
    process.exit(0);
  } else {
    log('\n✅ ALL CHECKS PASSED', GREEN);
    log('The UI should show status as: Connected', GREEN);
    process.exit(0);
  }
}

// Run the health check
main().catch((e) => {
  error(`\nUnexpected error: ${e.message}`);
  console.error(e);
  process.exit(1);
});




