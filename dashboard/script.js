// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// Chart instances
let timeChart, levelChart, hostChart;

// Initialize charts
function initCharts() {
    // Time series chart
    const timeCtx = document.getElementById('timeChart').getContext('2d');
    timeChart = new Chart(timeCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Log Count',
                data: [],
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });

    // Level distribution chart
    const levelCtx = document.getElementById('levelChart').getContext('2d');
    levelChart = new Chart(levelCtx, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#ef4444', // ERROR - red
                    '#f59e0b', // WARN - amber
                    '#10b981', // INFO - green
                    '#3b82f6', // DEBUG - blue
                    '#8b5cf6'  // OTHER - purple
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });

    // Host distribution chart
    const hostCtx = document.getElementById('hostChart').getContext('2d');
    hostChart = new Chart(hostCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Log Count',
                data: [],
                backgroundColor: '#764ba2',
                borderColor: '#5a3781',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// Update status indicator
function updateStatus(connected) {
    const indicator = document.getElementById('status-indicator');
    const text = document.getElementById('status-text');
    
    if (connected) {
        indicator.classList.remove('error');
        text.textContent = 'Connected';
        text.style.color = '#10b981';
    } else {
        indicator.classList.add('error');
        text.textContent = 'Connection Error';
        text.style.color = '#ef4444';
    }
}

// Fetch and update logs over time
async function updateLogsOverTime() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/logs/over-time`);
        if (!response.ok) throw new Error('Failed to fetch time data');
        
        const data = await response.json();
        
        const labels = data.map(item => {
            const date = new Date(item.ts);
            return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        });
        const counts = data.map(item => item.count);
        
        timeChart.data.labels = labels;
        timeChart.data.datasets[0].data = counts;
        timeChart.update();
        
        // Update total logs stat
        const total = counts.reduce((sum, count) => sum + count, 0);
        document.getElementById('total-logs').textContent = total.toLocaleString();
        
        return true;
    } catch (error) {
        console.error('Error updating time chart:', error);
        return false;
    }
}

// Fetch and update log levels
async function updateLogLevels() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/logs/levels`);
        if (!response.ok) throw new Error('Failed to fetch level data');
        
        const data = await response.json();
        
        const labels = data.map(item => item.level);
        const counts = data.map(item => item.count);
        
        levelChart.data.labels = labels;
        levelChart.data.datasets[0].data = counts;
        levelChart.update();
        
        // Update error and warning counts
        const errorItem = data.find(item => item.level === 'ERROR');
        const warnItem = data.find(item => item.level === 'WARN');
        
        document.getElementById('error-count').textContent = errorItem ? errorItem.count : 0;
        document.getElementById('warning-count').textContent = warnItem ? warnItem.count : 0;
        
        return true;
    } catch (error) {
        console.error('Error updating level chart:', error);
        return false;
    }
}

// Fetch and update top hosts
async function updateTopHosts() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/logs/top-hosts`);
        if (!response.ok) throw new Error('Failed to fetch host data');
        
        const data = await response.json();
        
        const labels = data.map(item => item.host);
        const counts = data.map(item => item.count);
        
        hostChart.data.labels = labels;
        hostChart.data.datasets[0].data = counts;
        hostChart.update();
        
        // Update active hosts count
        document.getElementById('host-count').textContent = data.length;
        
        return true;
    } catch (error) {
        console.error('Error updating host chart:', error);
        return false;
    }
}

// Refresh all data
async function refreshData() {
    const btn = document.getElementById('refresh-btn');
    btn.disabled = true;
    btn.textContent = '🔄 Loading...';
    
    try {
        const results = await Promise.all([
            updateLogsOverTime(),
            updateLogLevels(),
            updateTopHosts()
        ]);
        
        const allSuccess = results.every(r => r);
        updateStatus(allSuccess);
        
        // Update last update time
        const now = new Date();
        document.getElementById('last-update').textContent = now.toLocaleString();
        
    } catch (error) {
        console.error('Error refreshing data:', error);
        updateStatus(false);
    } finally {
        btn.disabled = false;
        btn.textContent = '🔄 Refresh';
    }
}

// Initialize dashboard
async function initDashboard() {
    initCharts();
    await refreshData();
    
    // Auto-refresh every 30 seconds
    setInterval(refreshData, 30000);
}

// Start dashboard when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}