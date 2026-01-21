# app.py - Admin Orders Management Application
import os
import sys
from datetime import datetime, timedelta
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

# ============================================
# ✅ DATABASE CONNECTION
# ============================================

def get_db_connection():
    """Establish database connection"""
    try:
        import psycopg
        from psycopg.rows import dict_row
        
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            print("⚠️ DATABASE_URL not found")
            return None
        
        # Fix for Render's postgres:// URL
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg.connect(database_url, row_factory=dict_row)
        print("✅ Database connected successfully!")
        return conn
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

# ============================================
# ✅ HELPER FUNCTIONS
# ============================================

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

# ============================================
# ✅ DATABASE FUNCTIONS
# ============================================

def get_todays_orders():
    """Get today's orders from database"""
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    o.order_id,
                    o.user_name,
                    o.user_phone,
                    o.total_amount,
                    o.status,
                    o.order_date,
                    COUNT(oi.order_item_id) as item_count
                FROM orders o
                LEFT JOIN order_items oi ON o.order_id = oi.order_id
                WHERE DATE(o.order_date) = CURRENT_DATE
                GROUP BY o.order_id
                ORDER BY o.order_date DESC
                LIMIT 20
            """)
            orders = cur.fetchall()
        
        conn.close()
        return orders
        
    except Exception as e:
        print(f"❌ Error getting today's orders: {e}")
        return []

def get_all_orders(page=1, per_page=20, status=None, search=None):
    """Get all orders with pagination"""
    try:
        conn = get_db_connection()
        if not conn:
            return [], 0
        
        offset = (page - 1) * per_page
        
        query = """
            SELECT 
                o.order_id,
                o.user_name,
                o.user_phone,
                o.user_email,
                o.total_amount,
                o.payment_mode,
                o.delivery_location,
                o.status,
                o.order_date,
                COUNT(oi.order_item_id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
        """
        
        conditions = []
        params = []
        
        if status:
            conditions.append("o.status = %s")
            params.append(status)
        
        if search:
            conditions.append("""
                (o.user_name ILIKE %s OR 
                 o.user_phone ILIKE %s OR 
                 o.user_email ILIKE %s OR 
                 CAST(o.order_id AS TEXT) ILIKE %s)
            """)
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param, search_param])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += """
            GROUP BY o.order_id
            ORDER BY o.order_date DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([per_page, offset])
        
        with conn.cursor() as cur:
            cur.execute(query, params)
            orders = cur.fetchall()
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM orders"
            if conditions:
                count_query += " WHERE " + " AND ".join(conditions)
                cur.execute(count_query, params[:-2])
            else:
                cur.execute(count_query)
            
            total = cur.fetchone()['total']
        
        conn.close()
        return orders, total
        
    except Exception as e:
        print(f"❌ Error getting all orders: {e}")
        return [], 0

def get_order_details(order_id):
    """Get complete order details"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        with conn.cursor() as cur:
            # Get order basic info
            cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
            order = cur.fetchone()
            
            if not order:
                conn.close()
                return None
            
            # Get order items
            cur.execute("""
                SELECT * FROM order_items 
                WHERE order_id = %s 
                ORDER BY order_item_id
            """, (order_id,))
            items = cur.fetchall()
            
            # Get customer details
            if order.get('user_id'):
                cur.execute("""
                    SELECT * FROM users 
                    WHERE id = %s 
                    LIMIT 1
                """, (order['user_id'],))
                customer = cur.fetchone()
                
                # Get addresses
                cur.execute("""
                    SELECT * FROM addresses 
                    WHERE user_id = %s 
                    ORDER BY is_default DESC
                """, (order['user_id'],))
                addresses = cur.fetchall()
                
                customer_data = {
                    'user': customer,
                    'addresses': addresses
                }
            else:
                customer_data = None
            
            # Get payment details
            cur.execute("SELECT * FROM payments WHERE order_id = %s LIMIT 1", (order_id,))
            payment = cur.fetchone()
        
        conn.close()
        
        return {
            'order': order,
            'items': items,
            'customer': customer_data,
            'payment': payment
        }
        
    except Exception as e:
        print(f"❌ Error getting order details: {e}")
        return None

def get_customers(page=1, per_page=20, search=None):
    """Get all customers with pagination"""
    try:
        conn = get_db_connection()
        if not conn:
            return [], 0
        
        offset = (page - 1) * per_page
        
        query = """
            SELECT 
                u.*,
                COUNT(o.order_id) as total_orders,
                COALESCE(SUM(o.total_amount), 0) as total_spent,
                MAX(o.order_date) as last_order_date
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
        """
        
        conditions = []
        params = []
        
        if search:
            conditions.append("""
                (u.full_name ILIKE %s OR 
                 u.phone ILIKE %s OR 
                 u.email ILIKE %s)
            """)
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += """
            GROUP BY u.id
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([per_page, offset])
        
        with conn.cursor() as cur:
            cur.execute(query, params)
            customers = cur.fetchall()
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM users"
            if conditions:
                count_query += " WHERE " + " AND ".join(conditions)
                cur.execute(count_query, params[:-2])
            else:
                cur.execute(count_query)
            
            total = cur.fetchone()['total']
        
        conn.close()
        return customers, total
        
    except Exception as e:
        print(f"❌ Error getting customers: {e}")
        return [], 0

def get_order_statistics(time_period='today'):
    """Get order statistics"""
    try:
        conn = get_db_connection()
        if not conn:
            return {
                'totals': {'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0},
                'top_items': [],
                'status_distribution': []
            }
        
        # Calculate date range
        now = datetime.now()
        
        if time_period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif time_period == 'week':
            start_date = now - timedelta(days=7)
            end_date = now
        elif time_period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        else:  # all time
            start_date = datetime.min
            end_date = now
        
        with conn.cursor() as cur:
            # Total statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    COALESCE(SUM(total_amount), 0) as total_revenue,
                    COALESCE(AVG(total_amount), 0) as avg_order_value
                FROM orders
                WHERE order_date BETWEEN %s AND %s
            """, (start_date, end_date))
            totals = cur.fetchone()
            
            # Most ordered items
            cur.execute("""
                SELECT 
                    oi.item_name,
                    oi.item_type,
                    SUM(oi.quantity) as total_quantity,
                    SUM(oi.total) as total_revenue
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.order_id
                WHERE o.order_date BETWEEN %s AND %s
                GROUP BY oi.item_name, oi.item_type
                ORDER BY total_quantity DESC
                LIMIT 10
            """, (start_date, end_date))
            top_items = cur.fetchall()
            
            # Orders by status
            cur.execute("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM orders
                WHERE order_date BETWEEN %s AND %s
                GROUP BY status
            """, (start_date, end_date))
            status_distribution = cur.fetchall()
        
        conn.close()
        
        return {
            'totals': totals or {'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0},
            'top_items': top_items or [],
            'status_distribution': status_distribution or []
        }
        
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
        return {
            'totals': {'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0},
            'top_items': [],
            'status_distribution': []
        }

# ============================================
# ✅ ADMIN LOGIN REQUIRED DECORATOR
# ============================================

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
        # Get today's orders
        todays_orders = get_todays_orders()
        
        # Get statistics
        stats = get_order_statistics('today')
        
        # Get quick stats
        today_stats = {'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0}
        pending_stats = {'pending': 0}
        customer_stats = {'new_customers': 0}
        
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                # Today's stats
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
                
                # New customers today
                cur.execute("""
                    SELECT COUNT(*) as new_customers 
                    FROM users 
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
                customer_stats = cur.fetchone() or customer_stats
            
            conn.close()
        
        return render_template('dashboard.html',
                             todays_orders=todays_orders,
                             today_stats=today_stats,
                             pending_stats=pending_stats,
                             customer_stats=customer_stats,
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
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        
        orders, total = get_all_orders(page=page, status=status, search=search)
        
        # Calculate pagination
        per_page = 20
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
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
        
        # Format currency
        for item in order_data['items']:
            item['price_formatted'] = format_currency(item.get('price', 0))
            item['total_formatted'] = format_currency(item.get('total', 0))
        
        order_data['order']['total_amount_formatted'] = format_currency(
            order_data['order'].get('total_amount', 0)
        )
        
        return jsonify({
            'success': True,
            'order': order_data['order'],
            'items': order_data['items'],
            'customer': order_data['customer'],
            'payment': order_data['payment']
        })
        
    except Exception as e:
        print(f"❌ Order details error: {e}")
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
                             page=page,
                             total_pages=total_pages,
                             total=total,
                             current_search=search,
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
        
        # Get statistics
        stats = get_order_statistics(time_period)
        
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
                             time_period=time_period,
                             format_currency=format_currency)
        
    except Exception as e:
        print(f"❌ Statistics page error: {e}")
        flash('Error loading statistics', 'error')
        return render_template('statistics.html',
                             stats={'totals': {'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0}},
                             time_period='today',
                             format_currency=format_currency)

# ============================================
# ✅ HEALTH CHECK ROUTE
# ============================================

@app.route('/admin/health')
def admin_health():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        db_status = 'connected' if conn else 'disconnected'
        
        if conn:
            conn.close()
        
        return jsonify({
            'status': 'healthy',
            'service': 'Bite Me Buddy Admin',
            'database': db_status,
            'timestamp': datetime.now().isoformat(),
            'timezone': 'Asia/Kolkata',
            'endpoints': {
                'login': '/admin/login',
                'dashboard': '/admin/dashboard',
                'orders': '/admin/orders',
                'customers': '/admin/customers',
                'statistics': '/admin/statistics',
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
            'failed': 'danger'
        }
        return status_classes.get(status.lower() if status else '', 'secondary')
    
    def get_admin_stats():
        try:
            conn = get_db_connection()
            if not conn:
                return {
                    'total_orders': 0,
                    'total_revenue': '₹0.00',
                    'total_customers': 0,
                    'pending_orders': 0
                }
            
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
            
            conn.close()
            
            return {
                'total_orders': total_orders,
                'total_revenue': format_currency(total_revenue),
                'total_customers': total_customers,
                'pending_orders': pending_orders
            }
        except Exception as e:
            print(f"⚠️ Stats error: {e}")
            return {
                'total_orders': 0,
                'total_revenue': '₹0.00',
                'total_customers': 0,
                'pending_orders': 0
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
    print("  • /admin/health  → Health check endpoint")
    
    is_render = os.environ.get('RENDER') is not None
    
    if not is_render:
        print("🚀 Starting in LOCAL DEVELOPMENT mode")
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        print("🚀 Starting in RENDER PRODUCTION mode")
        print("✅ Admin application ready for gunicorn")