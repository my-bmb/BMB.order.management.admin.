# app.py - Admin Orders Management Application
import os
import sys
from datetime import datetime
from functools import wraps
import traceback
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import ADMIN_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, ist_now, format_ist_datetime
    from models import get_db_connection, get_todays_orders, get_all_orders, get_order_details
    from models import update_order_status, get_customers, get_customer_details, get_order_statistics
    from utils import format_currency, generate_map_link, get_cloudinary_image_url, prepare_chart_data
    
    MODULES_LOADED = True
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    traceback.print_exc()
    MODULES_LOADED = False
    
    # Create dummy functions for testing
    def ist_now():
        return datetime.now()
    def format_ist_datetime(dt, fmt="%d %b %Y, %I:%M %p"):
        return dt.strftime(fmt) if dt else ""
    def format_currency(amt):
        return f"₹{amt:,.2f}"
    def generate_map_link(lat, lon):
        return f"https://maps.google.com?q={lat},{lon}" if lat and lon else None
    def get_cloudinary_image_url(url, folder=None):
        return url or "https://res.cloudinary.com/demo/image/upload/v1633427556/default_image.jpg"

# Flask App Setup
app = Flask(__name__, 
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)

app.secret_key = ADMIN_SECRET_KEY if 'ADMIN_SECRET_KEY' in globals() else 'dev-secret-key-123'

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
# ✅ DEFAULT ROUTES
# ============================================

@app.route('/')
def index():
    """Redirect to admin login"""
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_index():
    """Admin index page"""
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

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
        correct_username = ADMIN_USERNAME if 'ADMIN_USERNAME' in globals() else 'admin'
        correct_password = ADMIN_PASSWORD if 'ADMIN_PASSWORD' in globals() else 'admin123'
        
        if username == correct_username and password == correct_password:
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
    """Admin logout"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin_login'))

# ============================================
# ✅ DASHBOARD ROUTES
# ============================================

@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    """Admin Dashboard with Today's Orders and Statistics"""
    try:
        if not MODULES_LOADED:
            flash('Database modules not loaded. Using demo data.', 'warning')
            todays_orders = [
                {'order_id': 101, 'user_name': 'Demo User', 'total_amount': 450.00, 'status': 'pending', 'item_count': 2},
                {'order_id': 102, 'user_name': 'Test Customer', 'total_amount': 380.00, 'status': 'processing', 'item_count': 3}
            ]
            stats = {'totals': {'total_orders': 2, 'total_revenue': 830.00, 'avg_order_value': 415.00}}
            chart_data = {
                'timeline': {'labels': ['Today'], 'orders': [2], 'revenue': [830.00]},
                'items': {'labels': ['Demo Item'], 'quantities': [5], 'revenues': [830.00]},
                'status': {'labels': ['Pending', 'Processing'], 'values': [1, 1], 'colors': ['#ffc107', '#007bff']}
            }
            today_stats = {'total_orders': 2, 'total_revenue': 830.00, 'avg_order_value': 415.00}
            pending_stats = {'pending': 1}
            customer_stats = {'new_customers': 0}
        else:
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
            today_stats = {'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0}
            pending_stats = {'pending': 0}
            customer_stats = {'new_customers': 0}
            
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        # Total orders today
                        cur.execute("""
                            SELECT 
                                COUNT(*) as total_orders,
                                COALESCE(SUM(total_amount), 0) as total_revenue,
                                COALESCE(AVG(total_amount), 0) as avg_order_value
                            FROM orders
                            WHERE DATE(order_date) = CURRENT_DATE
                        """)
                        today_stats = cur.fetchone() or today_stats
                        
                        # Pending orders
                        cur.execute("SELECT COUNT(*) as pending FROM orders WHERE status = 'pending'")
                        pending_stats = cur.fetchone() or pending_stats
                        
                        # Recent customers
                        cur.execute("""
                            SELECT COUNT(*) as new_customers 
                            FROM users 
                            WHERE DATE(created_at) = CURRENT_DATE
                        """)
                        customer_stats = cur.fetchone() or customer_stats
            except Exception as e:
                print(f"⚠️ Stats error: {e}")
        
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
        print(f"❌ Dashboard error: {e}")
        traceback.print_exc()
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html',
                             todays_orders=[],
                             today_stats={'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0},
                             pending_stats={'pending': 0},
                             customer_stats={'new_customers': 0},
                             chart_data={
                                 'timeline': {'labels': [], 'orders': [], 'revenue': []},
                                 'items': {'labels': [], 'quantities': [], 'revenues': []},
                                 'status': {'labels': [], 'values': [], 'colors': []}
                             },
                             stats={'totals': {'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0}},
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
        if not MODULES_LOADED:
            flash('Database modules not loaded. Using demo data.', 'warning')
            orders = [
                {'order_id': 101, 'user_name': 'Demo User', 'user_phone': '+91 9876543210', 
                 'total_amount': 450.00, 'status': 'pending', 'item_count': 2, 
                 'order_date': datetime.now(), 'payment_status': 'pending'},
                {'order_id': 102, 'user_name': 'Test Customer', 'user_phone': '+91 9876543211',
                 'total_amount': 380.00, 'status': 'processing', 'item_count': 3,
                 'order_date': datetime.now(), 'payment_status': 'completed'}
            ]
            total = 2
            total_pages = 1
        else:
            page = request.args.get('page', 1, type=int)
            status = request.args.get('status', '')
            search = request.args.get('search', '')
            
            orders, total = get_all_orders(page=page, status=status, search=search)
            
            # Calculate pagination
            per_page = 20
            total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        return render_template('orders.html',
                             orders=orders,
                             page=1,
                             total_pages=total_pages,
                             total=total,
                             current_status='',
                             current_search='',
                             format_currency=format_currency,
                             format_ist_datetime=format_ist_datetime)
        
    except Exception as e:
        print(f"❌ Orders page error: {e}")
        flash(f'Error loading orders: {str(e)}', 'error')
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
        if not MODULES_LOADED:
            return jsonify({
                'success': False, 
                'message': 'Database modules not loaded'
            })
        
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
        
        # Format currency
        for item in order_data['items']:
            item['price_formatted'] = format_currency(item.get('price', 0))
            item['total_formatted'] = format_currency(item.get('total', 0))
        
        order_data['order']['total_amount_formatted'] = format_currency(
            order_data['order'].get('total_amount', 0)
        )
        
        # Get Cloudinary images for items
        for item in order_data['items']:
            if item.get('item_photo'):
                item['item_photo_url'] = get_cloudinary_image_url(
                    item['item_photo'],
                    'services' if item.get('item_type') == 'service' else 'menu_items'
                )
            else:
                item['item_photo_url'] = get_cloudinary_image_url(None)
        
        return jsonify({
            'success': True,
            'order': order_data['order'],
            'items': order_data['items'],
            'customer': order_data['customer'],
            'payment': order_data['payment'],
            'logs': order_data['logs']
        })
        
    except Exception as e:
        print(f"❌ Order details error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/order/<int:order_id>/payment')
@admin_login_required
def admin_order_payment(order_id):
    """Get payment details for modal"""
    try:
        if not MODULES_LOADED:
            return jsonify({'success': False, 'message': 'Database modules not loaded'})
        
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
                payment['amount_formatted'] = format_currency(payment.get('amount', 0))
                payment['total_amount_formatted'] = format_currency(payment.get('total_amount', 0))
                
                return jsonify({
                    'success': True,
                    'payment': payment
                })
                
    except Exception as e:
        print(f"❌ Payment details error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/order/<int:order_id>/customer')
@admin_login_required
def admin_order_customer(order_id):
    """Get customer details for modal"""
    try:
        if not MODULES_LOADED:
            return jsonify({'success': False, 'message': 'Database modules not loaded'})
        
        # First get order to get user_id
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM orders WHERE order_id = %s", (order_id,))
                order = cur.fetchone()
                
                if not order or not order.get('user_id'):
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
                        customer_data['stats'].get('total_spent', 0)
                    )
                    customer_data['stats']['avg_order_value_formatted'] = format_currency(
                        customer_data['stats'].get('avg_order_value', 0)
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
        print(f"❌ Customer details error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/order/<int:order_id>/update-status', methods=['POST'])
@admin_login_required
def admin_update_order_status(order_id):
    """Update order status"""
    try:
        if not MODULES_LOADED:
            return jsonify({'success': False, 'message': 'Database modules not loaded'})
        
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
        print(f"❌ Update status error: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ============================================
# ✅ CUSTOMERS MANAGEMENT ROUTES
# ============================================

@app.route('/admin/customers')
@admin_login_required
def admin_customers():
    """Customers Management Page"""
    try:
        if not MODULES_LOADED:
            flash('Database modules not loaded. Using demo data.', 'warning')
            customers = [
                {'id': 1, 'full_name': 'Demo User', 'phone': '+91 9876543210', 
                 'email': 'demo@email.com', 'total_orders': 2, 'total_spent': 830.00,
                 'created_at': datetime.now(), 'is_active': True}
            ]
            total = 1
            total_pages = 1
        else:
            page = request.args.get('page', 1, type=int)
            search = request.args.get('search', '')
            
            customers, total = get_customers(page=page, search=search)
            
            # Calculate pagination
            per_page = 20
            total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
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
                             page=1,
                             total_pages=total_pages,
                             total=total,
                             current_search='',
                             format_ist_datetime=format_ist_datetime)
        
    except Exception as e:
        print(f"❌ Customers page error: {e}")
        flash(f'Error loading customers: {str(e)}', 'error')
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
        
        if not MODULES_LOADED:
            flash('Database modules not loaded. Using demo data.', 'warning')
            stats = {
                'totals': {'total_orders': 15, 'total_revenue': 12500.00, 'avg_order_value': 833.33},
                'top_items': [
                    {'item_name': 'Pizza', 'total_quantity': 25, 'total_revenue': 6250.00},
                    {'item_name': 'Burger', 'total_quantity': 18, 'total_revenue': 3240.00}
                ],
                'status_distribution': [
                    {'status': 'delivered', 'count': 10},
                    {'status': 'pending', 'count': 3},
                    {'status': 'processing', 'count': 2}
                ]
            }
            chart_data = {
                'timeline': {
                    'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    'orders': [2, 3, 1, 4, 2, 2, 1],
                    'revenue': [1500, 2200, 800, 3200, 1600, 1800, 900]
                },
                'items': {
                    'labels': ['Pizza', 'Burger', 'Pasta', 'Salad', 'Coke'],
                    'quantities': [25, 18, 12, 8, 30],
                    'revenues': [6250, 3240, 2160, 1200, 1500]
                },
                'status': {
                    'labels': ['Delivered', 'Pending', 'Processing'],
                    'values': [10, 3, 2],
                    'colors': ['#28a745', '#ffc107', '#007bff']
                }
            }
        else:
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
                stats['totals'].get('total_revenue', 0)
            )
            stats['totals']['avg_order_value_formatted'] = format_currency(
                stats['totals'].get('avg_order_value', 0)
            )
        
        return render_template('statistics.html',
                             stats=stats,
                             chart_data=chart_data,
                             time_period=time_period,
                             format_currency=format_currency)
        
    except Exception as e:
        print(f"❌ Statistics page error: {e}")
        flash(f'Error loading statistics: {str(e)}', 'error')
        return render_template('statistics.html',
                             stats={},
                             chart_data={},
                             time_period='today',
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
        
        if not MODULES_LOADED:
            flash('Database modules not loaded. Using demo data.', 'warning')
            if item_type == 'services':
                items = [
                    {'id': 1, 'name': 'Home Cleaning', 'price': 500.00, 'final_price': 450.00, 
                     'discount': 50.00, 'category': 'Cleaning', 'photo': None,
                     'times_ordered': 5, 'total_quantity': 8, 'status': 'active'},
                    {'id': 2, 'name': 'Car Wash', 'price': 300.00, 'final_price': 270.00,
                     'discount': 30.00, 'category': 'Automotive', 'photo': None,
                     'times_ordered': 3, 'total_quantity': 5, 'status': 'active'}
                ]
            else:
                items = [
                    {'id': 1, 'name': 'Pizza', 'price': 250.00, 'final_price': 225.00,
                     'discount': 25.00, 'category': 'Italian', 'photo': None,
                     'times_ordered': 25, 'total_quantity': 30, 'status': 'active'},
                    {'id': 2, 'name': 'Burger', 'price': 120.00, 'final_price': 108.00,
                     'discount': 12.00, 'category': 'Fast Food', 'photo': None,
                     'times_ordered': 18, 'total_quantity': 22, 'status': 'active'}
                ]
        else:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    if item_type == 'services':
                        query = """
                            SELECT s.*, 
                                   COUNT(oi.order_item_id) as times_ordered,
                                   COALESCE(SUM(oi.quantity), 0) as total_quantity
                            FROM services s
                            LEFT JOIN order_items oi ON s.id = oi.item_id AND oi.item_type = 'service'
                            WHERE s.status = 'active'
                        """
                    else:
                        query = """
                            SELECT m.*, 
                                   COUNT(oi.order_item_id) as times_ordered,
                                   COALESCE(SUM(oi.quantity), 0) as total_quantity
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
        
        # Get Cloudinary images and format prices
        for item in items:
            if item.get('photo'):
                item['photo_url'] = get_cloudinary_image_url(
                    item['photo'],
                    'services' if item_type == 'services' else 'menu_items'
                )
            else:
                item['photo_url'] = get_cloudinary_image_url(None)
            
            # Format prices
            item['price_formatted'] = format_currency(item.get('price', 0))
            item['final_price_formatted'] = format_currency(item.get('final_price', 0))
            item['discount_formatted'] = format_currency(item.get('discount', 0))
        
        return render_template('items.html',
                             items=items,
                             item_type=item_type,
                             current_search=search,
                             format_currency=format_currency)
        
    except Exception as e:
        print(f"❌ Items page error: {e}")
        flash(f'Error loading items: {str(e)}', 'error')
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
        
        if not MODULES_LOADED:
            return jsonify({
                'success': True,
                'timeline': {'labels': ['Demo'], 'orders': [1], 'revenue': [100]},
                'items': {'labels': ['Demo'], 'quantities': [1], 'revenues': [100]},
                'status': {'labels': ['Demo'], 'values': [1], 'colors': ['#007bff']},
                'totals': {'total_orders': 1, 'total_revenue': 100, 'avg_order_value': 100}
            })
        
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
# ✅ HEALTH CHECK ROUTE
# ============================================

@app.route('/admin/health')
def admin_health():
    """Health check endpoint"""
    try:
        # Test database connection if modules are loaded
        if MODULES_LOADED:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                db_status = 'connected'
            except Exception as e:
                db_status = f'error: {str(e)}'
        else:
            db_status = 'modules_not_loaded'
        
        return jsonify({
            'status': 'healthy',
            'service': 'Bite Me Buddy Admin',
            'database': db_status,
            'modules_loaded': MODULES_LOADED,
            'timestamp': ist_now().isoformat(),
            'timezone': 'Asia/Kolkata',
            'endpoints': {
                'login': '/admin/login',
                'dashboard': '/admin/dashboard',
                'orders': '/admin/orders',
                'customers': '/admin/customers',
                'statistics': '/admin/statistics',
                'items': '/admin/items',
                'health': '/admin/health'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
            'timezone': 'UTC'
        }), 500

# ============================================
# ✅ CONTEXT PROCESSOR
# ============================================

@app.context_processor
def utility_processor():
    def get_admin_stats():
        """Get admin dashboard statistics"""
        try:
            if not MODULES_LOADED:
                return {
                    'total_orders': 15,
                    'total_revenue': '₹12,500.00',
                    'total_customers': 8,
                    'pending_orders': 3
                }
            
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Total orders
                    cur.execute("SELECT COUNT(*) as total FROM orders")
                    total_orders = cur.fetchone()['total']
                    
                    # Total revenue
                    cur.execute("SELECT COALESCE(SUM(total_amount), 0) as total FROM orders")
                    total_revenue = cur.fetchone()['total']
                    
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
            print(f"⚠️ Stats error: {e}")
            return {}
    
    def get_status_badge(status):
        """Get Bootstrap badge class for status"""
        status_classes = {
            'pending': 'warning',
            'confirmed': 'info',
            'processing': 'primary',
            'shipped': 'purple',
            'delivered': 'success',
            'cancelled': 'danger',
            'refunded': 'secondary'
        }
        return status_classes.get(status.lower() if status else '', 'secondary')
    
    def get_payment_badge(status):
        """Get Bootstrap badge class for payment status"""
        status_classes = {
            'pending': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'refunded': 'secondary',
            'processing': 'info'
        }
        return status_classes.get(status.lower() if status else '', 'secondary')
    
    return dict(
        ist_now=ist_now,
        format_ist_datetime=format_ist_datetime,
        format_currency=format_currency,
        get_admin_stats=get_admin_stats,
        get_status_badge=get_status_badge,
        get_payment_badge=get_payment_badge,
        MODULES_LOADED=MODULES_LOADED
    )

# ============================================
# ✅ ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500

# ============================================
# ✅ APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    print("🚀 Starting Bite Me Buddy Admin Application...")
    print(f"⏰ Current IST time: {ist_now().strftime('%d %b %Y, %I:%M %p')}")
    print(f"📦 Modules loaded: {MODULES_LOADED}")
    print("📊 Available Routes:")
    print("  • /              → Redirects to login")
    print("  • /admin         → Redirects to login")
    print("  • /admin/login   → Admin login page")
    print("  • /admin/dashboard → Admin dashboard")
    print("  • /admin/orders  → Orders management")
    print("  • /admin/customers → Customers management")
    print("  • /admin/statistics → Statistics & analytics")
    print("  • /admin/items   → Services & Menu items")
    print("  • /admin/health  → Health check endpoint")
    
    is_render = os.environ.get('RENDER') is not None
    
    if not is_render:
        print("🚀 Starting in LOCAL DEVELOPMENT mode")
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        print("🚀 Starting in RENDER PRODUCTION mode")
        print("✅ Admin application ready for gunicorn")
