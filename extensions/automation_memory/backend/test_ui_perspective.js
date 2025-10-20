#!/usr/bin/env node
/**
 * Test what the browser sees - simulates the exact UI health check
 */

const API_BASE = 'http://127.0.0.1:3051';

async function simulateUIHealthCheck() {
  console.log('\n🌐 Simulating UI Health Check (what the browser sees)...\n');
  
  try {
    console.log(`Fetching: ${API_BASE}/healthz`);
    const res = await fetch(`${API_BASE}/healthz`);
    const data = await res.json();
    
    console.log(`Response status: ${res.status}`);
    console.log(`Response data:`, data);
    
    const health = data.status === 'ok' ? 'Connected' : 'Error';
    
    console.log(`\n📊 UI Status: ${health}`);
    
    if (health === 'Connected') {
      console.log('✅ The UI should show: "Status: Connected" (green)');
    } else {
      console.log('⚠️  The UI will show: "Status: Error" (red)');
    }
    
    // Try loading actual data
    console.log('\n📦 Testing data endpoints...');
    const endpoints = [
      '/api/memories',
      '/api/task_flows', 
      '/api/scheduled_prompts'
    ];
    
    for (const endpoint of endpoints) {
      try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        const data = await response.json();
        console.log(`  ✓ ${endpoint}: ${Array.isArray(data) ? data.length : '?'} items`);
      } catch (e) {
        console.log(`  ✗ ${endpoint}: FAILED - ${e.message}`);
      }
    }
    
  } catch (e) {
    console.log(`\n❌ Connection failed: ${e.message}`);
    console.log('\n📊 UI Status: Disconnected');
    console.log('🔴 The UI will show: "Status: Disconnected" (red)');
  }
}

simulateUIHealthCheck();




