# app.py - Admin Orders Management Application
import os
import sys
from datetime import datetime, timedelta
from functools import wraps
import traceback
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import ADMIN_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, ist_now, format_ist_datetime
from models import get_db_connection, get_todays_orders, get_all_orders, get_order_details
from models import update_order_status, get_customers, get_customer_details, get_order_statistics
from utils import format_currency, generate_map_link, get_cloudinary_image_url, prepare_chart_data, get_time_period_dates

# Flask App Setup
app = Flask(__name__, 
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)
app.secret_key = ADMIN_SECRET_KEY

# Admin Login Required Decorator
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login as admin to access this page', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# ✅ AUTHENTICATION ROUTES
# ============================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return render_template('admin_login.html')
        
        # Check admin credentials
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session['login_time'] = ist_now().isoformat()
            
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'error')
            return render_template('admin_login.html')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin_login'))

# ============================================
# ✅ DASHBOARD ROUTES
# ============================================

@app.route('/admin/')
@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    """Admin Dashboard with Today's Orders and Statistics"""
    try:
        # Get today's orders
        todays_orders = get_todays_orders()
        
        # Get statistics for today
        stats = get_order_statistics('today')
        
        # Prepare chart data
        chart_data = prepare_chart_data(
            stats.get('orders_timeline', []),
            stats.get('top_items', []),
            stats.get('status_distribution', [])
        )
        
        # Get quick stats
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Total orders today
                today_start = ist_now().replace(hour=0, minute=0, second=0, microsecond=0)
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_orders,
                        SUM(total_amount) as total_revenue,
                        AVG(total_amount) as avg_order_value
                    FROM orders
                    WHERE DATE(order_date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata') = DATE(%s AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')
                """, (today_start,))
                today_stats = cur.fetchone()
                
                # Pending orders
                cur.execute("SELECT COUNT(*) as pending FROM orders WHERE status = 'pending'")
                pending_stats = cur.fetchone()
                
                # Recent customers
                cur.execute("""
                    SELECT COUNT(*) as new_customers 
                    FROM users 
                    WHERE DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata') = DATE(%s AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')
                """, (today_start,))
                customer_stats = cur.fetchone()
        
        return render_template('dashboard.html',
                             todays_orders=todays_orders,
                             today_stats=today_stats,
                             pending_stats=pending_stats,
                             customer_stats=customer_stats,
                             chart_data=chart_data,
                             stats=stats,
                             format_currency=format_currency,
                             format_ist_datetime=format_ist_datetime)
        
    except Exception as e:
        print(f"Dashboard error: {e}")
        traceback.print_exc()
        return render_template('dashboard.html',
                             todays_orders=[],
                             today_stats={},
                             pending_stats={},
                             customer_stats={},
                             chart_data={},
                             stats={},
                             format_currency=format_currency,
                             format_ist_datetime=format_ist_datetime)

# ============================================
# ✅ ORDERS MANAGEMENT ROUTES
# ============================================

@app.route('/admin/orders')
@admin_login_required
def admin_orders():
    """Orders Management Page"""
    try:
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        
        orders, total = get_all_orders(page=page, status=status, search=search)
        
        # Calculate pagination
        per_page = 20
        total_pages = (total + per_page - 1) // per_page
        
        return render_template('orders.html',
                             orders=orders,
                             page=page,
                             total_pages=total_pages,
                             total=total,
                             current_status=status,
                             current_search=search,
                             format_currency=format_currency,
                             format_ist_datetime=format_ist_datetime)
        
    except Exception as e:
        print(f"Orders page error: {e}")
        return render_template('orders.html',
                             orders=[],
                             page=1,
                             total_pages=0,
                             total=0,
                             current_status='',
                             current_search='',
                             format_currency=format_currency,
                             format_ist_datetime=format_ist_datetime)

@app.route('/admin/order/<int:order_id>')
@admin_login_required
def admin_order_details(order_id):
    """Get order details for modal"""
    try:
        order_data = get_order_details(order_id)
        
        if not order_data:
            return jsonify({'success': False, 'message': 'Order not found'})
        
        # Format dates
        if order_data['order'].get('order_date'):
            order_data['order']['order_date_formatted'] = format_ist_datetime(
                order_data['order']['order_date']
            )
        
        if order_data['order'].get('delivery_date'):
            order_data['order']['delivery_date_formatted'] = format_ist_datetime(
                order_data['order']['delivery_date']
            )
        
        if order_data['order'].get('payment_date'):
            order_data['order']['payment_date_formatted'] = format_ist_datetime(
                order_data['order']['payment_date']
            )
        
        # Format currency
        for item in order_data['items']:
            item['price_formatted'] = format_currency(item['price'])
            item['total_formatted'] = format_currency(item['total'])
        
        order_data['order']['total_amount_formatted'] = format_currency(
            order_data['order']['total_amount']
        )
        
        # Get Cloudinary images for items
        for item in order_data['items']:
            if item['item_photo']:
                item['item_photo_url'] = get_cloudinary_image_url(
                    item['item_photo'],
                    'services' if item['item_type'] == 'service' else 'menu_items'
                )
            else:
                item['item_photo_url'] = get_cloudinary_image_url(None)
        
        return jsonify({
            'success': True,
            'order': order_data['order'],
            'items': order_data['items'],
            'logs': order_data['logs']
        })
        
    except Exception as e:
        print(f"Order details error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/order/<int:order_id>/payment')
@admin_login_required
def admin_order_payment(order_id):
    """Get payment details for modal"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        p.*,
                        o.total_amount,
                        o.user_name,
                        o.order_date
                    FROM payments p
                    JOIN orders o ON p.order_id = o.order_id
                    WHERE p.order_id = %s
                """, (order_id,))
                
                payment = cur.fetchone()
                
                if not payment:
                    return jsonify({'success': False, 'message': 'Payment not found'})
                
                # Format dates
                if payment.get('payment_date'):
                    payment['payment_date_formatted'] = format_ist_datetime(
                        payment['payment_date']
                    )
                
                if payment.get('order_date'):
                    payment['order_date_formatted'] = format_ist_datetime(
                        payment['order_date']
                    )
                
                # Format currency
                payment['amount_formatted'] = format_currency(payment['amount'])
                payment['total_amount_formatted'] = format_currency(payment['total_amount'])
                
                return jsonify({
                    'success': True,
                    'payment': payment
                })
                
    except Exception as e:
        print(f"Payment details error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/order/<int:order_id>/customer')
@admin_login_required
def admin_order_customer(order_id):
    """Get customer details for modal"""
    try:
        # First get order to get user_id
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM orders WHERE order_id = %s", (order_id,))
                order = cur.fetchone()
                
                if not order or not order['user_id']:
                    return jsonify({'success': False, 'message': 'Customer not found'})
                
                user_id = order['user_id']
                
                # Get customer details
                customer_data = get_customer_details(user_id)
                
                if not customer_data:
                    return jsonify({'success': False, 'message': 'Customer details not found'})
                
                # Format dates
                if customer_data['user'].get('created_at'):
                    customer_data['user']['created_at_formatted'] = format_ist_datetime(
                        customer_data['user']['created_at']
                    )
                
                if customer_data['user'].get('last_login'):
                    customer_data['user']['last_login_formatted'] = format_ist_datetime(
                        customer_data['user']['last_login']
                    )
                
                # Format currency for stats
                if customer_data['stats']:
                    customer_data['stats']['total_spent_formatted'] = format_currency(
                        customer_data['stats']['total_spent'] or 0
                    )
                    customer_data['stats']['avg_order_value_formatted'] = format_currency(
                        customer_data['stats']['avg_order_value'] or 0
                    )
                
                # Generate map links for addresses
                for address in customer_data['addresses']:
                    if address.get('latitude') and address.get('longitude'):
                        address['map_link'] = generate_map_link(
                            address['latitude'],
                            address['longitude']
                        )
                
                return jsonify({
                    'success': True,
                    'customer': customer_data['user'],
                    'addresses': customer_data['addresses'],
                    'stats': customer_data['stats'],
                    'orders': customer_data['orders']
                })
                
    except Exception as e:
        print(f"Customer details error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/order/<int:order_id>/update-status', methods=['POST'])
@admin_login_required
def admin_update_order_status(order_id):
    """Update order status"""
    try:
        new_status = request.form.get('status', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status is required'})
        
        success, message = update_order_status(
            order_id, 
            new_status, 
            admin_id=session.get('admin_username'),
            notes=notes
        )
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        print(f"Update status error: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ============================================
# ✅ CUSTOMERS MANAGEMENT ROUTES
# ============================================

@app.route('/admin/customers')
@admin_login_required
def admin_customers():
    """Customers Management Page"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        customers, total = get_customers(page=page, search=search)
        
        # Calculate pagination
        per_page = 20
        total_pages = (total + per_page - 1) // per_page
        
        # Format dates and currency
        for customer in customers:
            if customer.get('created_at'):
                customer['created_at_formatted'] = format_ist_datetime(customer['created_at'])
            
            if customer.get('last_order_date'):
                customer['last_order_date_formatted'] = format_ist_datetime(customer['last_order_date'])
            
            if customer.get('total_spent'):
                customer['total_spent_formatted'] = format_currency(customer['total_spent'])
        
        return render_template('customers.html',
                             customers=customers,
                             page=page,
                             total_pages=total_pages,
                             total=total,
                             current_search=search,
                             format_ist_datetime=format_ist_datetime)
        
    except Exception as e:
        print(f"Customers page error: {e}")
        return render_template('customers.html',
                             customers=[],
                             page=1,
                             total_pages=0,
                             total=0,
                             current_search='',
                             format_ist_datetime=format_ist_datetime)

# ============================================
# ✅ STATISTICS ROUTES
# ============================================

@app.route('/admin/statistics')
@admin_login_required
def admin_statistics():
    """Statistics Page"""
    try:
        time_period = request.args.get('period', 'today')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # Get statistics
        stats = get_order_statistics(time_period)
        
        # Prepare chart data
        chart_data = prepare_chart_data(
            stats.get('orders_timeline', []),
            stats.get('top_items', []),
            stats.get('status_distribution', [])
        )
        
        # Format totals
        if stats.get('totals'):
            stats['totals']['total_revenue_formatted'] = format_currency(
                stats['totals']['total_revenue'] or 0
            )
            stats['totals']['avg_order_value_formatted'] = format_currency(
                stats['totals']['avg_order_value'] or 0
            )
        
        return render_template('statistics.html',
                             stats=stats,
                             chart_data=chart_data,
                             time_period=time_period,
                             start_date=start_date,
                             end_date=end_date,
                             format_currency=format_currency)
        
    except Exception as e:
        print(f"Statistics page error: {e}")
        return render_template('statistics.html',
                             stats={},
                             chart_data={},
                             time_period='today',
                             start_date='',
                             end_date='',
                             format_currency=format_currency)

# ============================================
# ✅ ITEMS MANAGEMENT ROUTES
# ============================================

@app.route('/admin/items')
@admin_login_required
def admin_items():
    """Items Management Page (Services & Menu)"""
    try:
        item_type = request.args.get('type', 'services')
        search = request.args.get('search', '')
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if item_type == 'services':
                    query = """
                        SELECT s.*, 
                               COUNT(oi.order_item_id) as times_ordered,
                               SUM(oi.quantity) as total_quantity
                        FROM services s
                        LEFT JOIN order_items oi ON s.id = oi.item_id AND oi.item_type = 'service'
                        WHERE s.status = 'active'
                    """
                else:
                    query = """
                        SELECT m.*, 
                               COUNT(oi.order_item_id) as times_ordered,
                               SUM(oi.quantity) as total_quantity
                        FROM menu m
                        LEFT JOIN order_items oi ON m.id = oi.item_id AND oi.item_type = 'menu'
                        WHERE m.status = 'active'
                    """
                
                conditions = []
                params = []
                
                if search:
                    conditions.append("name ILIKE %s")
                    params.append(f"%{search}%")
                
                if conditions:
                    query += " AND " + " AND ".join(conditions)
                
                query += " GROUP BY id ORDER BY position, name"
                
                cur.execute(query, params)
                items = cur.fetchall()
                
                # Get Cloudinary images
                for item in items:
                    if item['photo']:
                        item['photo_url'] = get_cloudinary_image_url(
                            item['photo'],
                            'services' if item_type == 'services' else 'menu_items'
                        )
                    else:
                        item['photo_url'] = get_cloudinary_image_url(None)
                    
                    # Format prices
                    item['price_formatted'] = format_currency(item['price'])
                    item['final_price_formatted'] = format_currency(item['final_price'])
                    item['discount_formatted'] = format_currency(item['discount'])
        
        return render_template('items.html',
                             items=items,
                             item_type=item_type,
                             current_search=search,
                             format_currency=format_currency)
        
    except Exception as e:
        print(f"Items page error: {e}")
        return render_template('items.html',
                             items=[],
                             item_type='services',
                             current_search='',
                             format_currency=format_currency)

# ============================================
# ✅ API ROUTES FOR CHARTS
# ============================================

@app.route('/admin/api/statistics')
@admin_login_required
def api_statistics():
    """API endpoint for chart data"""
    try:
        time_period = request.args.get('period', 'today')
        
        stats = get_order_statistics(time_period)
        chart_data = prepare_chart_data(
            stats.get('orders_timeline', []),
            stats.get('top_items', []),
            stats.get('status_distribution', [])
        )
        
        return jsonify({
            'success': True,
            'timeline': chart_data['timeline'],
            'items': chart_data['items'],
            'status': chart_data['status'],
            'totals': stats.get('totals', {})
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ============================================
# ✅ CONTEXT PROCESSOR
# ============================================

@app.context_processor
def utility_processor():
    def get_admin_stats():
        """Get admin dashboard statistics"""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Total orders
                    cur.execute("SELECT COUNT(*) as total FROM orders")
                    total_orders = cur.fetchone()['total']
                    
                    # Total revenue
                    cur.execute("SELECT SUM(total_amount) as total FROM orders")
                    total_revenue = cur.fetchone()['total'] or 0
                    
                    # Total customers
                    cur.execute("SELECT COUNT(*) as total FROM users")
                    total_customers = cur.fetchone()['total']
                    
                    # Pending orders
                    cur.execute("SELECT COUNT(*) as total FROM orders WHERE status = 'pending'")
                    pending_orders = cur.fetchone()['total']
                    
                    return {
                        'total_orders': total_orders,
                        'total_revenue': format_currency(total_revenue),
                        'total_customers': total_customers,
                        'pending_orders': pending_orders
                    }
        except Exception as e:
            print(f"Stats error: {e}")
            return {}
    
    def get_status_badge(status):
        """Get Bootstrap badge class for status"""
        status_classes = {
            'pending': 'badge-warning',
            'confirmed': 'badge-info',
            'processing': 'badge-primary',
            'shipped': 'badge-purple',
            'delivered': 'badge-success',
            'cancelled': 'badge-danger',
            'refunded': 'badge-secondary'
        }
        return status_classes.get(status.lower(), 'badge-secondary')
    
    def get_payment_badge(status):
        """Get Bootstrap badge class for payment status"""
        status_classes = {
            'pending': 'badge-warning',
            'completed': 'badge-success',
            'failed': 'badge-danger',
            'refunded': 'badge-secondary',
            'processing': 'badge-info'
        }
        return status_classes.get(status.lower(), 'badge-secondary')
    
    return dict(
        ist_now=ist_now,
        format_ist_datetime=format_ist_datetime,
        format_currency=format_currency,
        get_admin_stats=get_admin_stats,
        get_status_badge=get_status_badge,
        get_payment_badge=get_payment_badge
    )

# ============================================
# ✅ HEALTH CHECK
# ============================================

@app.route('/admin/health')
def admin_health():
    """Health check endpoint"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        
        return jsonify({
            'status': 'healthy',
            'service': 'Bite Me Buddy Admin',
            'database': 'connected',
            'timestamp': ist_now().isoformat(),
            'timezone': 'Asia/Kolkata'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': ist_now().isoformat(),
            'timezone': 'Asia/Kolkata'
        }), 500

# ============================================
# ✅ APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    print("🚀 Starting Bite Me Buddy Admin Application...")
    print(f"⏰ Current IST time: {ist_now().strftime('%d %b %Y, %I:%M %p')}")
    
    is_render = os.environ.get('RENDER') is not None
    
    if not is_render:
        print("🚀 Starting in LOCAL DEVELOPMENT mode")
        app.run(debug=True, host='0.0.0.0', port=5001)  # Different port from main app
    else:
        print("🚀 Starting in RENDER PRODUCTION mode")
        print("✅ Admin application ready")