# models.py - Database Models with Auto-Creation
import os
import sys
from datetime import datetime, timedelta
import traceback

# Add parent directory to path to import from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL, CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, ist_now, to_ist, format_ist_datetime

try:
    import psycopg
    from psycopg.rows import dict_row
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    
    # Configure Cloudinary
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )
except ImportError as e:
    print(f"⚠️ Import warning: {e}")

def get_db_connection():
    """Establish database connection using DATABASE_URL from environment"""
    try:
        # Use config.py se DATABASE_URL
        database_url = DATABASE_URL
        
        if not database_url:
            print("⚠️ DATABASE_URL not found in environment")
            # Try to use default for local development
            database_url = "postgresql://postgres:postgres@localhost:5432/bite_me_buddy"
        
        # Fix for Render's postgres:// URL
        if database_url and database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
            print(f"🔧 Fixed DATABASE_URL format")
        
        print(f"🔗 Connecting to database...")
        
        # Add connection timeout and retry
        conn = psycopg.connect(
            database_url, 
            row_factory=dict_row,
            connect_timeout=10
        )
        print(f"✅ Database connected successfully!")
        return conn
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        
        # For development, create a dummy connection
        if os.environ.get('RENDER') is None:
            print("⚠️ Using dummy data for development")
            class DummyConn:
                def cursor(self):
                    class DummyCursor:
                        def execute(self, *args, **kwargs):
                            return None
                        def fetchone(self):
                            return {'exists': False}
                        def fetchall(self):
                            return []
                        def __enter__(self):
                            return self
                        def __exit__(self, *args):
                            pass
                    return DummyCursor()
                def commit(self):
                    pass
                def close(self):
                    pass
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
            return DummyConn()
        else:
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
                result = cur.fetchone()
                admin_table_exists = result['exists'] if result else False
                
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
                            order_id INTEGER,
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
                            payment_id INTEGER,
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
                        try:
                            cur.execute("""
                                INSERT INTO admin_settings (setting_key, setting_value, setting_type, description)
                                VALUES (%s, %s, %s, %s)
                            """, setting)
                        except Exception as e:
                            print(f"⚠️ Error inserting setting {setting[0]}: {e}")
                    
                    conn.commit()
                    print("✅ Admin tables created successfully!")
                else:
                    print("✅ Admin tables already exist")
                
    except Exception as e:
        print(f"⚠️ Error initializing admin tables: {e}")
        traceback.print_exc()

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
                    WHERE DATE(o.order_date) >= %s
                    GROUP BY o.order_id
                    ORDER BY o.order_date DESC
                    LIMIT 50
                """, (today_start.date(),))
                
                return cur.fetchall()
    except Exception as e:
        print(f"⚠️ Error getting today's orders: {e}")
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
                
                result = cur.fetchone()
                total = result['total'] if result else 0
                
                return orders, total
    except Exception as e:
        print(f"⚠️ Error getting all orders: {e}")
        return [], 0

def get_order_details(order_id):
    """Get complete order details"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get order basic info
                cur.execute("""
                    SELECT 
                        o.*
                    FROM orders o
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
                        END as full_name
                    FROM order_items oi
                    LEFT JOIN services s ON oi.item_type = 'service' AND oi.item_id = s.id
                    LEFT JOIN menu m ON oi.item_type = 'menu' AND oi.item_id = m.id
                    WHERE oi.order_id = %s
                    ORDER BY oi.order_item_id
                """, (order_id,))
                
                items = cur.fetchall()
                
                # Get customer details
                if order.get('user_id'):
                    cur.execute("""
                        SELECT 
                            u.*,
                            a.*
                        FROM users u
                        LEFT JOIN addresses a ON u.id = a.user_id AND a.is_default = TRUE
                        WHERE u.id = %s
                        LIMIT 1
                    """, (order['user_id'],))
                    
                    customer = cur.fetchone()
                else:
                    customer = None
                
                # Get payment details
                cur.execute("""
                    SELECT * FROM payments 
                    WHERE order_id = %s
                    LIMIT 1
                """, (order_id,))
                
                payment = cur.fetchone()
                
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
                    'payment': payment,
                    'logs': logs
                }
    except Exception as e:
        print(f"⚠️ Error getting order details: {e}")
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
                    start_date = datetime.min
                    end_date = now
                    group_by = "DATE_TRUNC('month', order_date)"
                
                # Orders per time period
                cur.execute(f"""
                    SELECT 
                        {group_by} as period,
                        COUNT(*) as order_count,
                        COALESCE(SUM(total_amount), 0) as total_revenue
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
                        COALESCE(SUM(oi.quantity), 0) as total_quantity,
                        COALESCE(SUM(oi.total), 0) as total_revenue
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
                        COALESCE(SUM(total_amount), 0) as total_revenue,
                        COALESCE(AVG(total_amount), 0) as avg_order_value
                    FROM orders
                    WHERE order_date BETWEEN %s AND %s
                """, (start_date, end_date))
                
                totals = cur.fetchone()
                
                return {
                    'orders_timeline': orders_data,
                    'top_items': top_items,
                    'status_distribution': status_data,
                    'totals': totals or {'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0}
                }
    except Exception as e:
        print(f"⚠️ Error getting statistics: {e}")
        return {
            'orders_timeline': [],
            'top_items': [],
            'status_distribution': [],
            'totals': {'total_orders': 0, 'total_revenue': 0, 'avg_order_value': 0}
        }

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
                    VALUES