// admin.js - Admin Panel JavaScript
$(document).ready(function() {
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    // Format dates in local timezone
    $('.date-time').each(function() {
        var dateText = $(this).text();
        if (dateText) {
            var date = new Date(dateText);
            if (!isNaN(date)) {
                $(this).text(date.toLocaleString('en-IN', {
                    timeZone: 'Asia/Kolkata',
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true
                }));
            }
        }
    });
    
    // Order Details Modal
    $(document).on('click', '.view-order-details', function() {
        var orderId = $(this).data('order-id');
        showOrderDetails(orderId);
    });
    
    // Payment Details Modal
    $(document).on('click', '.view-payment-details', function() {
        var orderId = $(this).data('order-id');
        showPaymentDetails(orderId);
    });
    
    // Customer Details Modal
    $(document).on('click', '.view-customer-details', function() {
        var orderId = $(this).data('order-id');
        showCustomerDetails(orderId);
    });
    
    // Update Status Modal
    $(document).on('click', '.update-status', function() {
        var orderId = $(this).data('order-id');
        var currentStatus = $(this).data('current-status');
        showUpdateStatusModal(orderId, currentStatus);
    });
    
    // Modal Close Handlers
    $(document).on('click', '.modal-close, .modal-backdrop', function() {
        closeAllModals();
    });
    
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });
    
    // Status Filter
    $('#status-filter').change(function() {
        var status = $(this).val();
        var url = new URL(window.location);
        
        if (status) {
            url.searchParams.set('status', status);
        } else {
            url.searchParams.delete('status');
        }
        
        window.location.href = url.toString();
    });
    
    // Search Form
    $('#search-form').submit(function(e) {
        e.preventDefault();
        var search = $('#search-input').val();
        var url = new URL(window.location);
        
        if (search) {
            url.searchParams.set('search', search);
        } else {
            url.searchParams.delete('search');
        }
        
        url.searchParams.delete('page');
        window.location.href = url.toString();
    });
    
    // Time Period Filter
    $('.time-period-btn').click(function() {
        var period = $(this).data('period');
        var url = new URL(window.location);
        
        url.searchParams.set('period', period);
        window.location.href = url.toString();
    });
    
    // Refresh Dashboard Button
    $('#refresh-dashboard').click(function() {
        location.reload();
    });
    
    // Initialize Charts
    initializeCharts();
});

// Show Order Details Modal
function showOrderDetails(orderId) {
    showLoading('Loading order details...');
    
    $.ajax({
        url: `/admin/order/${orderId}`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                var order = response.order;
                var items = response.items;
                var logs = response.logs;
                
                var modalHtml = `
                <div class="modal" id="order-details-modal">
                    <div class="modal-header">
                        <h3 class="modal-title">Order #${order.order_id}</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h4>Order Information</h4>
                                <table class="table table-sm">
                                    <tr>
                                        <td><strong>Customer:</strong></td>
                                        <td>${order.user_name}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Phone:</strong></td>
                                        <td>${order.user_phone}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Email:</strong></td>
                                        <td>${order.user_email}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Order Date:</strong></td>
                                        <td>${order.order_date_formatted}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Status:</strong></td>
                                        <td><span class="badge badge-${getStatusClass(order.status)}">${order.status}</span></td>
                                    </tr>
                                    <tr>
                                        <td><strong>Total Amount:</strong></td>
                                        <td><strong>${order.total_amount_formatted}</strong></td>
                                    </tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h4>Delivery Information</h4>
                                <table class="table table-sm">
                                    <tr>
                                        <td><strong>Delivery Location:</strong></td>
                                        <td>${order.delivery_location}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Payment Mode:</strong></td>
                                        <td>${order.payment_mode}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Payment Status:</strong></td>
                                        <td><span class="badge badge-${getPaymentStatusClass(order.payment_status)}">${order.payment_status}</span></td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                        
                        <h4 class="mt-4">Order Items</h4>
                        <div class="table-responsive">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>Item</th>
                                        <th>Type</th>
                                        <th>Price</th>
                                        <th>Quantity</th>
                                        <th>Total</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                items.forEach(function(item) {
                    modalHtml += `
                    <tr>
                        <td>
                            <div class="d-flex align-items-center">
                                <img src="${item.item_photo_url || '/static/img/default-item.png'}" 
                                     alt="${item.item_name}" 
                                     class="rounded mr-2" 
                                     style="width: 40px; height: 40px; object-fit: cover;">
                                <div>
                                    <strong>${item.item_name}</strong><br>
                                    <small class="text-muted">${item.full_description || ''}</small>
                                </div>
                            </div>
                        </td>
                        <td><span class="badge badge-info">${item.item_type}</span></td>
                        <td>${item.price_formatted}</td>
                        <td>${item.quantity}</td>
                        <td><strong>${item.total_formatted}</strong></td>
                    </tr>
                    `;
                });
                
                modalHtml += `
                                </tbody>
                            </table>
                        </div>
                        
                        <h4 class="mt-4">Order Timeline</h4>
                        <div class="timeline">
                `;
                
                if (logs && logs.length > 0) {
                    logs.forEach(function(log) {
                        modalHtml += `
                        <div class="timeline-item">
                            <div class="timeline-marker"></div>
                            <div class="timeline-content">
                                <p class="mb-1"><strong>${log.action}</strong></p>
                                <p class="text-muted small mb-1">${formatDateTime(log.created_at)}</p>
                                <p class="mb-0">${log.details || 'No details'}</p>
                                ${log.old_status ? `<p class="mb-0"><small>Status: ${log.old_status} → ${log.new_status}</small></p>` : ''}
                            </div>
                        </div>
                        `;
                    });
                } else {
                    modalHtml += `<p class="text-muted">No timeline data available</p>`;
                }
                
                modalHtml += `
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-outline modal-close">Close</button>
                        <button class="btn btn-primary update-status" data-order-id="${order.order_id}" data-current-status="${order.status}">
                            Update Status
                        </button>
                    </div>
                </div>
                `;
                
                showModal(modalHtml);
            } else {
                showError('Failed to load order details: ' + response.message);
            }
        },
        error: function(xhr, status, error) {
            showError('Error loading order details: ' + error);
        }
    });
}

// Show Payment Details Modal
function showPaymentDetails(orderId) {
    showLoading('Loading payment details...');
    
    $.ajax({
        url: `/admin/order/${orderId}/payment`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                var payment = response.payment;
                
                var modalHtml = `
                <div class="modal" id="payment-details-modal">
                    <div class="modal-header">
                        <h3 class="modal-title">Payment Details for Order #${orderId}</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h4>Payment Information</h4>
                                <table class="table table-sm">
                                    <tr>
                                        <td><strong>Customer:</strong></td>
                                        <td>${payment.user_name}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Amount:</strong></td>
                                        <td><strong>${payment.amount_formatted}</strong></td>
                                    </tr>
                                    <tr>
                                        <td><strong>Payment Mode:</strong></td>
                                        <td>${payment.payment_mode}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Status:</strong></td>
                                        <td><span class="badge badge-${getPaymentStatusClass(payment.payment_status)}">${payment.payment_status}</span></td>
                                    </tr>
                                    <tr>
                                        <td><strong>Payment Date:</strong></td>
                                        <td>${payment.payment_date_formatted || 'N/A'}</td>
                                    </tr>
                                </table>
                            </div>
                            <div class="col-md-6">
                                <h4>Transaction Details</h4>
                                <table class="table table-sm">
                `;
                
                if (payment.transaction_id) {
                    modalHtml += `
                    <tr>
                        <td><strong>Transaction ID:</strong></td>
                        <td><code>${payment.transaction_id}</code></td>
                    </tr>
                    `;
                }
                
                if (payment.razorpay_order_id) {
                    modalHtml += `
                    <tr>
                        <td><strong>Razorpay Order ID:</strong></td>
                        <td><code>${payment.razorpay_order_id}</code></td>
                    </tr>
                    `;
                }
                
                if (payment.razorpay_payment_id) {
                    modalHtml += `
                    <tr>
                        <td><strong>Razorpay Payment ID:</strong></td>
                        <td><code>${payment.razorpay_payment_id}</code></td>
                    </tr>
                    `;
                }
                
                if (payment.razorpay_signature) {
                    modalHtml += `
                    <tr>
                        <td><strong>Signature:</strong></td>
                        <td><code class="small">${payment.razorpay_signature.substring(0, 30)}...</code></td>
                    </tr>
                    `;
                }
                
                modalHtml += `
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-outline modal-close">Close</button>
                    </div>
                </div>
                `;
                
                showModal(modalHtml);
            } else {
                showError('Failed to load payment details: ' + response.message);
            }
        },
        error: function(xhr, status, error) {
            showError('Error loading payment details: ' + error);
        }
    });
}

// Show Customer Details Modal
function showCustomerDetails(orderId) {
    showLoading('Loading customer details...');
    
    $.ajax({
        url: `/admin/order/${orderId}/customer`,
        method: 'GET',
        success: function(response) {
            if (response.success) {
                var customer = response.customer;
                var addresses = response.addresses || [];
                var stats = response.stats || {};
                var orders = response.orders || [];
                
                var modalHtml = `
                <div class="modal" id="customer-details-modal">
                    <div class="modal-header">
                        <h3 class="modal-title">Customer Details</h3>
                        <button class="modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-4 text-center">
                                <img src="${customer.profile_pic || '/static/img/default-avatar.png'}" 
                                     alt="${customer.full_name}" 
                                     class="rounded-circle mb-3" 
                                     style="width: 100px; height: 100px; object-fit: cover;">
                                <h4>${customer.full_name}</h4>
                                <p class="text-muted">${customer.is_active ? 'Active' : 'Inactive'}</p>
                            </div>
                            <div class="col-md-8">
                                <h4>Contact Information</h4>
                                <table class="table table-sm">
                                    <tr>
                                        <td><strong>Phone:</strong></td>
                                        <td>${customer.phone}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Email:</strong></td>
                                        <td>${customer.email}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Location:</strong></td>
                                        <td>${customer.location || 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Member Since:</strong></td>
                                        <td>${customer.created_at_formatted || 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Last Login:</strong></td>
                                        <td>${customer.last_login_formatted || 'Never'}</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                        
                        <div class="row mt-4">
                            <div class="col-md-4">
                                <div class="stat-card small">
                                    <div class="stat-icon orders">
                                        <i class="fas fa-shopping-bag"></i>
                                    </div>
                                    <div class="stat-info">
                                        <h3>${stats.total_orders || 0}</h3>
                                        <p>Total Orders</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="stat-card small">
                                    <div class="stat-icon revenue">
                                        <i class="fas fa-rupee-sign"></i>
                                    </div>
                                    <div class="stat-info">
                                        <h3>${stats.total_spent_formatted || '₹0.00'}</h3>
                                        <p>Total Spent</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="stat-card small">
                                    <div class="stat-icon customers">
                                        <i class="fas fa-tag"></i>
                                    </div>
                                    <div class="stat-info">
                                        <h3>${stats.avg_order_value_formatted || '₹0.00'}</h3>
                                        <p>Avg. Order</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <h4 class="mt-4">Addresses</h4>
                `;
                
                if (addresses.length > 0) {
                    addresses.forEach(function(address, index) {
                        var mapLink = address.map_link ? 
                            `<a href="${address.map_link}" target="_blank" class="btn btn-sm btn-outline">
                                <i class="fas fa-map-marker-alt"></i> View on Map
                            </a>` : '';
                        
                        modalHtml += `
                        <div class="card mb-2">
                            <div class="card-body">
                                <div class="d-flex justify-content-between">
                                    <div>
                                        <h5 class="card-title mb-1">
                                            ${address.full_name}
                                            ${address.is_default ? '<span class="badge badge-primary ml-2">Default</span>' : ''}
                                        </h5>
                                        <p class="card-text mb-1">
                                            ${address.address_line1}<br>
                                            ${address.address_line2 ? address.address_line2 + '<br>' : ''}
                                            ${address.landmark ? 'Landmark: ' + address.landmark + '<br>' : ''}
                                            ${address.city}, ${address.state} - ${address.pincode}
                                        </p>
                                        <p class="card-text">
                                            <small class="text-muted">Phone: ${address.phone}</small>
                                        </p>
                                    </div>
                                    <div>
                                        ${mapLink}
                                    </div>
                                </div>
                            </div>
                        </div>
                        `;
                    });
                } else {
                    modalHtml += `<p class="text-muted">No addresses found</p>`;
                }
                
                if (orders.length > 0) {
                    modalHtml += `
                        <h4 class="mt-4">Recent Orders</h4>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Order ID</th>
                                        <th>Date</th>
                                        <th>Amount</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;
                    
                    orders.forEach(function(order) {
                        modalHtml += `
                        <tr>
                            <td><a href="#" class="view-order-details" data-order-id="${order.order_id}">#${order.order_id}</a></td>
                            <td>${formatDateTime(order.order_date)}</td>
                            <td>₹${parseFloat(order.total_amount).toFixed(2)}</td>
                            <td><span class="badge badge-${getStatusClass(order.status)}">${order.status}</span></td>
                        </tr>
                        `;
                    });
                    
                    modalHtml += `
                                </tbody>
                            </table>
                        </div>
                    `;
                }
                
                modalHtml += `
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-outline modal-close">Close</button>
                    </div>
                </div>
                `;
                
                showModal(modalHtml);
            } else {
                showError('Failed to load customer details: ' + response.message);
            }
        },
        error: function(xhr, status, error) {
            showError('Error loading customer details: ' + error);
        }
    });
}

// Show Update Status Modal
function showUpdateStatusModal(orderId, currentStatus) {
    var modalHtml = `
    <div class="modal" id="update-status-modal">
        <div class="modal-header">
            <h3 class="modal-title">Update Order Status</h3>
            <button class="modal-close">&times;</button>
        </div>
        <form id="update-status-form">
            <div class="modal-body">
                <input type="hidden" name="order_id" value="${orderId}">
                <div class="form-group">
                    <label for="status">Status</label>
                    <select class="form-control" id="status" name="status" required>
                        <option value="pending" ${currentStatus === 'pending' ? 'selected' : ''}>Pending</option>
                        <option value="confirmed" ${currentStatus === 'confirmed' ? 'selected' : ''}>Confirmed</option>
                        <option value="processing" ${currentStatus === 'processing' ? 'selected' : ''}>Processing</option>
                        <option value="shipped" ${currentStatus === 'shipped' ? 'selected' : ''}>Shipped</option>
                        <option value="delivered" ${currentStatus === 'delivered' ? 'selected' : ''}>Delivered</option>
                        <option value="cancelled" ${currentStatus === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="notes">Notes (Optional)</label>
                    <textarea class="form-control" id="notes" name="notes" rows="3" placeholder="Add any notes about this status change..."></textarea>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-outline modal-close">Cancel</button>
                <button type="submit" class="btn btn-primary">Update Status</button>
            </div>
        </form>
    </div>
    `;
    
    showModal(modalHtml);
    
    // Handle form submission
    $('#update-status-form').submit(function(e) {
        e.preventDefault();
        
        var formData = $(this).serialize();
        
        $.ajax({
            url: `/admin/order/${orderId}/update-status`,
            method: 'POST',
            data: formData,
            success: function(response) {
                if (response.success) {
                    showSuccess(response.message);
                    closeAllModals();
                    setTimeout(function() {
                        location.reload();
                    }, 1000);
                } else {
                    showError(response.message);
                }
            },
            error: function(xhr, status, error) {
                showError('Error updating status: ' + error);
            }
        });
    });
}

// Initialize Charts
function initializeCharts() {
    // Orders Timeline Chart
    if ($('#orders-timeline-chart').length) {
        var ctx = $('#orders-timeline-chart')[0].getContext('2d');
        var chartData = JSON.parse($('#orders-timeline-chart').attr('data-chart') || '{}');
        
        if (chartData.labels && chartData.labels.length > 0) {
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: 'Orders',
                        data: chartData.orders,
                        borderColor: '#4361ee',
                        backgroundColor: 'rgba(67, 97, 238, 0.1)',
                        tension: 0.3
                    }, {
                        label: 'Revenue',
                        data: chartData.revenue,
                        borderColor: '#4cc9f0',
                        backgroundColor: 'rgba(76, 201, 240, 0.1)',
                        tension: 0.3,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Orders'
                            }
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
                            }
                        }
                    }
                }
            });
        }
    }
    
    // Top Items Chart
    if ($('#top-items-chart').length) {
        var ctx = $('#top-items-chart')[0].getContext('2d');
        var chartData = JSON.parse($('#top-items-chart').attr('data-chart') || '{}');
        
        if (chartData.labels && chartData.labels.length > 0) {
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: 'Quantity Sold',
                        data: chartData.quantities,
                        backgroundColor: '#4361ee',
                        borderColor: '#4361ee',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    indexAxis: 'y',
                    scales: {
                        x: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Quantity'
                            }
                        }
                    }
                }
            });
        }
    }
    
    // Status Distribution Chart
    if ($('#status-distribution-chart').length) {
        var ctx = $('#status-distribution-chart')[0].getContext('2d');
        var chartData = JSON.parse($('#status-distribution-chart').attr('data-chart') || '{}');
        
        if (chartData.labels && chartData.labels.length > 0) {
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        data: chartData.values,
                        backgroundColor: chartData.colors,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
    }
}

// Helper Functions
function showModal(html) {
    $('body').append('<div class="modal-backdrop"></div>');
    $('body').append(html);
    $('.modal-backdrop, .modal').fadeIn(200);
}

function closeAllModals() {
    $('.modal-backdrop, .modal').fadeOut(200, function() {
        $(this).remove();
    });
}

function showLoading(message) {
    showModal(`
    <div class="modal" id="loading-modal">
        <div class="modal-body text-center">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="sr-only">Loading...</span>
            </div>
            <p>${message}</p>
        </div>
    </div>
    `);
}

function showSuccess(message) {
    var alertHtml = `
    <div class="alert alert-success alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
            <span aria-hidden="true">&times;</span>
        </button>
    </div>
    `;
    
    $('.main-content').prepend(alertHtml);
    
    setTimeout(function() {
        $('.alert-success').alert('close');
    }, 3000);
}

function showError(message) {
    var alertHtml = `
    <div class="alert alert-danger alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
            <span aria-hidden="true">&times;</span>
        </button>
    </div>
    `;
    
    $('.main-content').prepend(alertHtml);
}

function getStatusClass(status) {
    var classes = {
        'pending': 'warning',
        'confirmed': 'info',
        'processing': 'primary',
        'shipped': 'purple',
        'delivered': 'success',
        'cancelled': 'danger',
        'refunded': 'secondary'
    };
    return classes[status.toLowerCase()] || 'secondary';
}

function getPaymentStatusClass(status) {
    var classes = {
        'pending': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'refunded': 'secondary',
        'processing': 'info'
    };
    return classes[status.toLowerCase()] || 'secondary';
}

function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return 'N/A';
    
    var date = new Date(dateTimeStr);
    if (isNaN(date)) return dateTimeStr;
    
    return date.toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}
