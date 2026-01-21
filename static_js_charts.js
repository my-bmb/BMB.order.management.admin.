// charts.js - Additional Chart Functions
$(document).ready(function() {
    // Initialize dashboard charts
    initializeDashboardCharts();
    
    // Auto-refresh charts every 5 minutes
    setInterval(function() {
        refreshCharts();
    }, 300000);
});

function initializeDashboardCharts() {
    // Check if charts exist on page
    if ($('#orders-timeline-chart').length) {
        loadChartData();
    }
}

function loadChartData() {
    var timePeriod = getCurrentTimePeriod();
    
    $.ajax({
        url: '/admin/api/statistics',
        method: 'GET',
        data: { period: timePeriod },
        success: function(response) {
            if (response.success) {
                updateCharts(response);
            }
        },
        error: function(xhr, status, error) {
            console.error('Error loading chart data:', error);
        }
    });
}

function refreshCharts() {
    var currentPath = window.location.pathname;
    
    if (currentPath.includes('/admin/statistics') || currentPath === '/admin/' || currentPath === '/admin/dashboard') {
        loadChartData();
    }
}

function updateCharts(data) {
    // Update Orders Timeline Chart
    if (data.timeline && data.timeline.labels.length > 0) {
        updateOrdersChart(data.timeline);
    }
    
    // Update Top Items Chart
    if (data.items && data.items.labels.length > 0) {
        updateItemsChart(data.items);
    }
    
    // Update Status Distribution Chart
    if (data.status && data.status.labels.length > 0) {
        updateStatusChart(data.status);
    }
}

function updateOrdersChart(timelineData) {
    var ctx = $('#orders-timeline-chart')[0];
    
    if (!ctx || !ctx.chart) {
        // Create new chart if doesn't exist
        ctx = ctx.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: timelineData.labels,
                datasets: [{
                    label: 'Orders',
                    data: timelineData.orders,
                    borderColor: '#4361ee',
                    backgroundColor: 'rgba(67, 97, 238, 0.1)',
                    tension: 0.3
                }, {
                    label: 'Revenue',
                    data: timelineData.revenue,
                    borderColor: '#4cc9f0',
                    backgroundColor: 'rgba(76, 201, 240, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y1'
                }]
            },
            options: getOrdersChartOptions()
        });
    } else {
        // Update existing chart
        var chart = ctx.chart;
        chart.data.labels = timelineData.labels;
        chart.data.datasets[0].data = timelineData.orders;
        chart.data.datasets[1].data = timelineData.revenue;
        chart.update();
    }
}

function updateItemsChart(itemsData) {
    var ctx = $('#top-items-chart')[0];
    
    if (!ctx || !ctx.chart) {
        ctx = ctx.getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: itemsData.labels,
                datasets: [{
                    label: 'Quantity Sold',
                    data: itemsData.quantities,
                    backgroundColor: '#4361ee',
                    borderColor: '#4361ee',
                    borderWidth: 1
                }]
            },
            options: getItemsChartOptions()
        });
    } else {
        var chart = ctx.chart;
        chart.data.labels = itemsData.labels;
        chart.data.datasets[0].data = itemsData.quantities;
        chart.update();
    }
}

function updateStatusChart(statusData) {
    var ctx = $('#status-distribution-chart')[0];
    
    if (!ctx || !ctx.chart) {
        ctx = ctx.getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: statusData.labels,
                datasets: [{
                    data: statusData.values,
                    backgroundColor: statusData.colors,
                    borderWidth: 1
                }]
            },
            options: getStatusChartOptions()
        });
    } else {
        var chart = ctx.chart;
        chart.data.labels = statusData.labels;
        chart.data.datasets[0].data = statusData.values;
        chart.data.datasets[0].backgroundColor = statusData.colors;
        chart.update();
    }
}

function getOrdersChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: 'index',
            intersect: false
        },
        scales: {
            x: {
                grid: {
                    display: false
                },
                ticks: {
                    maxRotation: 0
                }
            },
            y: {
                type: 'linear',
                display: true,
                position: 'left',
                title: {
                    display: true,
                    text: 'Orders'
                },
                beginAtZero: true
            },
            y1: {
                type: 'linear',
                display: true,
                position: 'right',
                title: {
                    display: true,
                    text: 'Revenue (₹)'
                },
                grid: {
                    drawOnChartArea: false
                },
                beginAtZero: true
            }
        },
        plugins: {
            tooltip: {
                mode: 'index',
                intersect: false
            },
            legend: {
                position: 'top'
            }
        }
    };
}

function getItemsChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        scales: {
            x: {
                beginAtZero: true,
                title: {
                    display: true,
                    text: 'Quantity'
                }
            }
        },
        plugins: {
            legend: {
                display: false
            }
        }
    };
}

function getStatusChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom'
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        var label = context.label || '';
                        var value = context.raw || 0;
                        var total = context.dataset.data.reduce((a, b) => a + b, 0);
                        var percentage = Math.round((value / total) * 100);
                        return label + ': ' + value + ' (' + percentage + '%)';
                    }
                }
            }
        }
    };
}

function getCurrentTimePeriod() {
    var url = new URL(window.location);
    return url.searchParams.get('period') || 'today';
}

// Export function for other scripts
window.adminCharts = {
    refresh: refreshCharts,
    load: loadChartData
};