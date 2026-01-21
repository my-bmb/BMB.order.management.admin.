# app.py - Admin Orders Management Application
import os
import sys
from datetime import datetime
from functools import wraps
import traceback
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Flask App Setup
app = Flask(__name__, 
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)

app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'dev-secret-key-123')

# Helper functions
def ist_now():
    return datetime.now()

def format_ist_datetime(dt, fmt="%d %b %Y, %I:%M %p"):
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except:
            return dt
    try:
        return dt.strftime(fmt)
    except:
        return str(dt)

def format_currency(amount):
    try:
        if amount is None:
            return "₹0.00"
        amount_float = float(amount)
        return f"₹{amount_float:,.2f}"
    except:
        return "₹0.00"

def generate_map_link(lat, lon):
    if lat and lon:
        return f"https://maps.google.com?q={lat},{lon}"
    return None

def get_cloudinary_image_url(url, folder=None):
    if url and url.startswith('http'):
        return url
    return "https://res.cloudinary.com/demo/image/upload/v1633427556/default_image.jpg"

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
        correct_username = os.environ.get('ADMIN_USERNAME', 'admin')
        correct_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        
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
    """Admin Dashboard with Today's Orders"""
    try:
        # Create demo data for testing
        todays_orders = [
            {
                'order_id': 101, 
                'user_name': 'Demo User', 
                'total_amount': 450.00, 
                'status': 'pending', 
                'item_count': 2, 
                'order_date': datetime.now(),
                'user_phone': '+91 9876543210'
            },
            {
                'order_id': 102, 
                'user_name': 'Test Customer', 
                'total_amount': 380.00, 
                'status': 'processing', 
                'item_count': 3, 
                'order_date': datetime.now(),
                'user_phone': '+91 9876543211'
            }
        ]
        
        today_stats = {'total_orders': 2, 'total_revenue': 830.00, 'avg_order_value': 415.00}
        pending_stats = {'pending': 1}
        customer_stats = {'new_customers': 0}
        
        # Create SIMPLE chart data (NO COMPLEX OBJECTS)
        chart_data = {
            'timeline': {
                'labels': ['9 AM', '10 AM', '11 AM', '12 PM', '1 PM'],
                'orders': [2, 5, 3, 7, 4],
                'revenue': [1000, 2500, 1500, 3500, 2000]
            },
            'items': {
                'labels': ['Pizza', 'Burger', 'Pasta', 'Salad'],
                'quantities': [25, 18, 12, 8],
                'revenues': [6250, 3240, 2160, 1200]
            },
            'status': {
                'labels': ['Pending', 'Processing', 'Delivered'],
                'values': [3, 2, 10],
                'colors': ['#ffc107', '#007bff', '#28a745']
            }
        }
        
        stats = {
            'totals': {'total_orders': 15, 'total_revenue': 12500.00, 'avg_order_value': 833.33},
            'top_items': [
                {'item_name': 'Pizza', 'total_quantity': 25, 'total_revenue': 6250.00},
                {'item_name': 'Burger', 'total_quantity': 18, 'total_revenue': 3240.00}
            ]
        }
        
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
        flash('Error loading dashboard', 'error')
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
        # Demo data
        orders = [
            {
                'order_id': 101, 
                'user_name': 'Demo User', 
                'user_phone': '+91 9876543210',
                'user_email': 'demo@email.com', 
                'total_amount': 450.00, 
                'status': 'pending', 
                'item_count': 2, 
                'order_date': datetime.now(),
                'payment_mode': 'COD',
                'delivery_location': 'Test Address'
            },
            {
                'order_id': 102, 
                'user_name': 'Test Customer', 
                'user_phone': '+91 9876543211',
                'user_email': 'test@email.com', 
                'total_amount': 380.00, 
                'status': 'processing', 
                'item_count': 3, 
                'order_date': datetime.now(),
                'payment_mode': 'Online',
                'delivery_location': 'Test Address 2'
            }
        ]
        
        return render_template('orders.html',
                             orders=orders,
                             page=1,
                             total_pages=1,
                             total=2,
                             current_status='',
                             current_search='',
                             format_currency=format_currency,
                             format_ist_datetime=format_ist_datetime)
        
    except Exception as e:
        print(f"❌ Orders page error: {e}")
        flash('Error loading orders', 'error')
        return render_template('orders.html',
                             orders=[],
                             page=1,
                             total_pages=0,
                             total=0,
                             current_status='',
                             current_search='',
                             format_currency=format_currency,
                             format_ist_datetime=format_ist_datetime)

# ============================================
# ✅ CUSTOMERS MANAGEMENT ROUTES
# ============================================

@app.route('/admin/customers')
@admin_login_required
def admin_customers():
    """Customers Management Page"""
    try:
        # Demo data
        customers = [
            {
                'id': 1, 
                'full_name': 'Demo User', 
                'phone': '+91 9876543210',
                'email': 'demo@email.com', 
                'total_orders': 2, 
                'total_spent': 830.00,
                'created_at': datetime.now(), 
                'is_active': True, 
                'profile_pic': None
            },
            {
                'id': 2, 
                'full_name': 'Test Customer', 
                'phone': '+91 9876543211',
                'email': 'test@email.com', 
                'total_orders': 1, 
                'total_spent': 450.00,
                'created_at': datetime.now(), 
                'is_active': True, 
                'profile_pic': None
            }
        ]
        
        # Format dates and currency
        for customer in customers:
            customer['created_at_formatted'] = format_ist_datetime(customer['created_at'])
            customer['total_spent_formatted'] = format_currency(customer['total_spent'])
        
        return render_template('customers.html',
                             customers=customers,
                             page=1,
                             total_pages=1,
                             total=2,
                             current_search='',
                             format_ist_datetime=format_ist_datetime)
        
    except Exception as e:
        print(f"❌ Customers page error: {e}")
        flash('Error loading customers', 'error')
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
        
        # Demo data
        stats = {
            'totals': {
                'total_orders': 15, 
                'total_revenue': 12500.00, 
                'avg_order_value': 833.33,
                'total_revenue_formatted': format_currency(12500.00),
                'avg_order_value_formatted': format_currency(833.33)
            },
            'top_items': [
                {'item_name': 'Pizza', 'total_quantity': 25, 'total_revenue': 6250.00, 'item_type': 'menu'},
                {'item_name': 'Burger', 'total_quantity': 18, 'total_revenue': 3240.00, 'item_type': 'menu'}
            ],
            'status_distribution': [
                {'status': 'delivered', 'count': 10},
                {'status': 'pending', 'count': 3},
                {'status': 'processing', 'count': 2}
            ]
        }
        
        # Create SIMPLE chart data
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
        
        return render_template('statistics.html',
                             stats=stats,
                             chart_data=chart_data,
                             time_period=time_period,
                             format_currency=format_currency)
        
    except Exception as e:
        print(f"❌ Statistics page error: {e}")
        flash('Error loading statistics', 'error')
        return render_template('statistics.html',
                             stats={},
                             chart_data={
                                 'timeline': {'labels': [], 'orders': [], 'revenue': []},
                                 'items': {'labels': [], 'quantities': [], 'revenues': []},
                                 'status': {'labels': [], 'values': [], 'colors': []}
                             },
                             time_period='today',
                             format_currency=format_currency)

# ============================================
# ✅ ITEMS MANAGEMENT ROUTES
# ============================================

@app.route('/admin/items')
@admin_login_required
def admin_items():
    """Items Management Page"""
    try:
        item_type = request.args.get('type', 'services')
        search = request.args.get('search', '')
        
        # Demo data
        if item_type == 'services':
            items = [
                {
                    'id': 1, 
                    'name': 'Home Cleaning', 
                    'price': 500.00, 
                    'final_price': 450.00,
                    'discount': 50.00, 
                    'category': 'Cleaning', 
                    'photo': None,
                    'times_ordered': 5, 
                    'total_quantity': 8, 
                    'status': 'active',
                    'description': 'Professional home cleaning'
                },
                {
                    'id': 2, 
                    'name': 'Car Wash', 
                    'price': 300.00, 
                    'final_price': 270.00,
                    'discount': 30.00, 
                    'category': 'Automotive', 
                    'photo': None,
                    'times_ordered': 3, 
                    'total_quantity': 5, 
                    'status': 'active',
                    'description': 'Complete car wash'
                }
            ]
        else:
            items = [
                {
                    'id': 1, 
                    'name': 'Pizza', 
                    'price': 250.00, 
                    'final_price': 225.00,
                    'discount': 25.00, 
                    'category': 'Italian', 
                    'photo': None,
                    'times_ordered': 25, 
                    'total_quantity': 30, 
                    'status': 'active',
                    'description': 'Delicious cheese pizza'
                },
                {
                    'id': 2, 
                    'name': 'Burger', 
                    'price': 120.00, 
                    'final_price': 108.00,
                    'discount': 12.00, 
                    'category': 'Fast Food', 
                    'photo': None,
                    'times_ordered': 18, 
                    'total_quantity': 22, 
                    'status': 'active',
                    'description': 'Juicy burger'
                }
            ]
        
        # Format prices
        for item in items:
            item['photo_url'] = get_cloudinary_image_url(item.get('photo'))
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
        flash('Error loading items', 'error')
        return render_template('items.html',
                             items=[],
                             item_type='services',
                             current_search='',
                             format_currency=format_currency)

# ============================================
# ✅ HEALTH CHECK ROUTE
# ============================================

@app.route('/admin/health')
def admin_health():
    """Health check endpoint"""
    try:
        return jsonify({
            'status': 'healthy',
            'service': 'Bite Me Buddy Admin',
            'timestamp': datetime.now().isoformat(),
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
            'timestamp': datetime.now().isoformat()
        }), 500

# ============================================
# ✅ CONTEXT PROCESSOR
# ============================================

@app.context_processor
def utility_processor():
    def get_status_badge(status):
        status_classes = {
            'pending': 'warning',
            'confirmed': 'info',
            'processing': 'primary',
            'shipped': 'purple',
            'delivered': 'success',
            'cancelled': 'danger'
        }
        return status_classes.get(status.lower() if status else '', 'secondary')
    
    def get_payment_badge(status):
        status_classes = {
            'pending': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'refunded': 'secondary'
        }
        return status_classes.get(status.lower() if status else '', 'secondary')
    
    def get_admin_stats():
        return {
            'total_orders': 15,
            'total_revenue': '₹12,500.00',
            'total_customers': 8,
            'pending_orders': 3
        }
    
    return dict(
        ist_now=ist_now,
        format_ist_datetime=format_ist_datetime,
        format_currency=format_currency,
        get_admin_stats=get_admin_stats,
        get_status_badge=get_status_badge,
        get_payment_badge=get_payment_badge
    )

# ============================================
# ✅ APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    print("🚀 Starting Bite Me Buddy Admin Application...")
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
