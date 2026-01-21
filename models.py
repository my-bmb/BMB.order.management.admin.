# models.py - Database Models with Auto-Creation
import os
import sys
from datetime import datetime
import traceback
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Add parent directory to path to import from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL, CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, ist_now, to_ist, format_ist_datetime

import psycopg
from psycopg.rows import dict_row

# Configure Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

def get_db_connection():
    """Establish database connection using DATABASE_URL from environment"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Fix for Render's postgres:// URL
    database_url = DATABASE_URL
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        conn = psycopg.connect(database_url, row_factory=dict_row)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        raise

def init_admin_tables():
    """Initialize admin-specific tables if they don't exist"""
    try:
        print(f"🔗 Connecting to database for admin tables...")
        with get_db_connection() as conn:
            print(f"✅ Database connected successfully!")
            
            with conn.cursor() as cur:
                # Check if admin_settings table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'admin_settings'
                    )
                """)
                admin_table_exists = cur.fetchone()['exists']
                
                if not admin_table_exists:
                    print("📦 Creating admin tables...")
                    
                    # ✅ ADMIN SETTINGS TABLE
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS admin_settings (
                            id SERIAL PRIMARY KEY,
                            setting_key VARCHAR(100) UNIQUE NOT NULL,
                            setting_value TEXT,
                            setting_type VARCHAR(50),
                            description TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # ✅ ORDER LOGS TABLE
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS order_logs (
                            log_id SERIAL PRIMARY KEY,
                            order_id INTEGER REFERENCES orders(order_id) ON DELETE CASCADE,
                            admin_id INTEGER,
                            action VARCHAR(50) NOT NULL,
                            details TEXT,
                            old_status VARCHAR(50),
                            new_status VARCHAR(50),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # ✅ PAYMENT LOGS TABLE
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS payment_logs (
                            log_id SERIAL PRIMARY KEY,
                            payment_id INTEGER REFERENCES payments(payment_id) ON DELETE CASCADE,
                            admin_id INTEGER,
                            action VARCHAR(50) NOT NULL,
                            details TEXT,
                            old_status VARCHAR(50),
                            new_status VARCHAR(50),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # ✅ ADMIN NOTIFICATIONS TABLE
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS admin_notifications (
                            notification_id SERIAL PRIMARY KEY,
                            title VARCHAR(100) NOT NULL,
                            message TEXT NOT NULL,
                            notification_type VARCHAR(50),
                            is_read BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            read_at TIMESTAMP
                        )
                    """)
                    
                    # ✅ CREATE INDEXES FOR PERFORMANCE
                    print("📊 Creating admin indexes...")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_order_logs_order_id ON order_logs(order_id)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_logs_payment_id ON payment_logs(payment_id)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_notifications_read ON admin_notifications(is_read)")
                    
                    # Insert default admin settings
                    print("📝 Adding default admin settings...")
                    
                    default_settings = [
                        ('site_name', 'Bite Me Buddy Admin', 'text', 'Website name displayed in admin panel'),
                        ('currency_symbol', '₹', 'text', 'Currency symbol for display'),
                        ('timezone', 'Asia/Kolkata', 'text', 'Default timezone'),
                        ('items_per_page', '20', 'number', 'Number of items per page in lists'),
                        ('default_order_status', 'pending', 'text', 'Default status for new orders'),
                        ('enable_email_notifications', 'true', 'boolean', 'Enable email notifications'),
                        ('enable_sms_notifications', 'true', 'boolean', 'Enable SMS notifications'),
                        ('order_notification_email', 'admin@bitemebuddy.com', 'text', 'Email for order notifications')
                    ]
                    
                    for setting in default_settings:
                        cur.execute("""
                            INSERT INTO admin_settings (setting_key, setting_value, setting_type, description)
                            VALUES (%s, %s, %s, %s)
                        """, setting)
                    
                    conn.commit()
                    print("✅ Admin tables created successfully!")
                else:
                    print("✅ Admin tables already exist")
                
    except Exception as e:
        print(f"❌ Error initializing admin tables: {e}")
        traceback.print_exc()
        raise

def get_todays_orders():
    """Get today's orders"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                today_start = ist_now().replace(hour=0, minute=0, second=0, microsecond=0)
                
                cur.execute("""
                    SELECT 
                        o.order_id,
                        o.user_name,
                        o.user_phone,
                        o.total_amount,
                        o.payment_mode,
                        o.delivery_location,
                        o.status,
                        o.order_date,
                        COUNT(oi.order_item_id) as item_count
                    FROM orders o
                    LEFT JOIN order_items oi ON o.order_id = oi.order_id
                    WHERE DATE(o.order_date AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata') = DATE(%s AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata')
                    GROUP BY o.order_id
                    ORDER BY o.order_date DESC
                """, (today_start,))
                
                return cur.fetchall()
    except Exception as e:
        print(f"Error getting today's orders: {e}")
        return []

def get_all_orders(page=1, per_page=20, status=None, search=None):
    """Get all orders with pagination and filters"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
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
                        o.delivery_date,
                        COUNT(oi.order_item_id) as item_count,
                        p.payment_status
                    FROM orders o
                    LEFT JOIN order_items oi ON o.order_id = oi.order_id
                    LEFT JOIN payments p ON o.order_id = p.order_id
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
                    GROUP BY o.order_id, p.payment_status
                    ORDER BY o.order_date DESC
                    LIMIT %s OFFSET %s
                """
                
                params.extend([per_page, offset])
                
                cur.execute(query, params)
                orders = cur.fetchall()
                
                # Get total count
                count_query = """
                    SELECT COUNT(DISTINCT o.order_id) as total
                    FROM orders o
                """
                
                if conditions:
                    count_query += " WHERE " + " AND ".join(conditions)
                    count_params = params[:-2]  # Remove LIMIT and OFFSET params
                    cur.execute(count_query, count_params)
                else:
                    cur.execute(count_query)
                
                total = cur.fetchone()['total']
                
                return orders, total
    except Exception as e:
        print(f"Error getting all orders: {e}")
        return [], 0

def get_order_details(order_id):
    """Get complete order details"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get order basic info
                cur.execute("""
                    SELECT 
                        o.*,
                        p.payment_status,
                        p.transaction_id,
                        p.razorpay_order_id,
                        p.razorpay_payment_id,
                        p.razorpay_signature,
                        p.payment_date
                    FROM orders o
                    LEFT JOIN payments p ON o.order_id = p.order_id
                    WHERE o.order_id = %s
                """, (order_id,))
                
                order = cur.fetchone()
                
                if not order:
                    return None
                
                # Get order items
                cur.execute("""
                    SELECT 
                        oi.*,
                        CASE 
                            WHEN oi.item_type = 'service' THEN s.name
                            WHEN oi.item_type = 'menu' THEN m.name
                            ELSE 'Unknown Item'
                        END as full_name,
                        CASE 
                            WHEN oi.item_type = 'service' THEN s.description
                            WHEN oi.item_type = 'menu' THEN m.description
                            ELSE ''
                        END as full_description
                    FROM order_items oi
                    LEFT JOIN services s ON oi.item_type = 'service' AND oi.item_id = s.id
                    LEFT JOIN menu m ON oi.item_type = 'menu' AND oi.item_id = m.id
                    WHERE oi.order_id = %s
                    ORDER BY oi.order_item_id
                """, (order_id,))
                
                items = cur.fetchall()
                
                # Get customer details
                if order['user_id']:
                    cur.execute("""
                        SELECT 
                            u.*,
                            a.*
                        FROM users u
                        LEFT JOIN addresses a ON u.id = a.user_id AND a.is_default = TRUE
                        WHERE u.id = %s
                    """, (order['user_id'],))
                    
                    customer = cur.fetchone()
                else:
                    customer = None
                
                # Get order logs
                cur.execute("""
                    SELECT * FROM order_logs 
                    WHERE order_id = %s 
                    ORDER BY created_at DESC
                """, (order_id,))
                
                logs = cur.fetchall()
                
                return {
                    'order': order,
                    'items': items,
                    'customer': customer,
                    'logs': logs
                }
    except Exception as e:
        print(f"Error getting order details: {e}")
        return None

def get_order_statistics(time_period='today'):
    """Get order statistics for different time periods"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                now = ist_now()
                
                if time_period == 'today':
                    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = now
                    group_by = "DATE_TRUNC('hour', order_date)"
                elif time_period == 'week':
                    start_date = now - timedelta(days=7)
                    end_date = now
                    group_by = "DATE(order_date)"
                elif time_period == 'month':
                    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    end_date = now
                    group_by = "DATE(order_date)"
                else:  # all time
                    start_date = datetime.min.replace(tzinfo=UTC_TIMEZONE).astimezone(IST_TIMEZONE)
                    end_date = now
                    group_by = "DATE_TRUNC('month', order_date)"
                
                # Orders per time period
                cur.execute(f"""
                    SELECT 
                        {group_by} as period,
                        COUNT(*) as order_count,
                        SUM(total_amount) as total_revenue
                    FROM orders
                    WHERE order_date BETWEEN %s AND %s
                    GROUP BY period
                    ORDER BY period
                """, (start_date, end_date))
                
                orders_data = cur.fetchall()
                
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
                
                status_data = cur.fetchall()
                
                # Total statistics
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_orders,
                        SUM(total_amount) as total_revenue,
                        AVG(total_amount) as avg_order_value
                    FROM orders
                    WHERE order_date BETWEEN %s AND %s
                """, (start_date, end_date))
                
                totals = cur.fetchone()
                
                return {
                    'orders_timeline': orders_data,
                    'top_items': top_items,
                    'status_distribution': status_data,
                    'totals': totals
                }
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return {}

def update_order_status(order_id, new_status, admin_id=None, notes=None):
    """Update order status and log the change"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get current status
                cur.execute("SELECT status FROM orders WHERE order_id = %s", (order_id,))
                current_order = cur.fetchone()
                
                if not current_order:
                    return False, "Order not found"
                
                old_status = current_order['status']
                
                # Update order status
                cur.execute("""
                    UPDATE orders 
                    SET status = %s 
                    WHERE order_id = %s
                """, (new_status, order_id))
                
                # Log the change
                cur.execute("""
                    INSERT INTO order_logs 
                    (order_id, admin_id, action, details, old_status, new_status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (order_id, admin_id, 'status_update', notes, old_status, new_status))
                
                conn.commit()
                
                return True, "Status updated successfully"
    except Exception as e:
        return False, str(e)

def get_customers(page=1, per_page=20, search=None):
    """Get all customers with pagination"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                offset = (page - 1) * per_page
                
                query = """
                    SELECT 
                        u.*,
                        COUNT(o.order_id) as total_orders,
                        SUM(o.total_amount) as total_spent,
                        MAX(o.order_date) as last_order_date,
                        a.address_line1,
                        a.city,
                        a.state
                    FROM users u
                    LEFT JOIN orders o ON u.id = o.user_id
                    LEFT JOIN addresses a ON u.id = a.user_id AND a.is_default = TRUE
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
                    GROUP BY u.id, a.address_line1, a.city, a.state
                    ORDER BY u.created_at DESC
                    LIMIT %s OFFSET %s
                """
                
                params.extend([per_page, offset])
                
                cur.execute(query, params)
                customers = cur.fetchall()
                
                # Get total count
                count_query = "SELECT COUNT(*) as total FROM users"
                if conditions:
                    count_query += " WHERE " + " AND ".join(conditions)
                    count_params = params[:-2]
                    cur.execute(count_query, count_params)
                else:
                    cur.execute(count_query)
                
                total = cur.fetchone()['total']
                
                return customers, total
    except Exception as e:
        print(f"Error getting customers: {e}")
        return [], 0

def get_customer_details(user_id):
    """Get complete customer details"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get user info
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cur.fetchone()
                
                if not user:
                    return None
                
                # Get addresses
                cur.execute("SELECT * FROM addresses WHERE user_id = %s ORDER BY is_default DESC", (user_id,))
                addresses = cur.fetchall()
                
                # Get orders
                cur.execute("""
                    SELECT * FROM orders 
                    WHERE user_id = %s 
                    ORDER BY order_date DESC
                    LIMIT 10
                """, (user_id,))
                
                orders = cur.fetchall()
                
                # Get order stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_orders,
                        SUM(total_amount) as total_spent,
                        AVG(total_amount) as avg_order_value
                    FROM orders 
                    WHERE user_id = %s
                """, (user_id,))
                
                stats = cur.fetchone()
                
                return {
                    'user': user,
                    'addresses': addresses,
                    'orders': orders,
                    'stats': stats
                }
    except Exception as e:
        print(f"Error getting customer details: {e}")
        return None

# Initialize admin tables on import
try:
    init_admin_tables()
    print("✅ Admin tables initialized successfully!")
except Exception as e:
    print(f"⚠️ Admin table initialization failed: {e}")
