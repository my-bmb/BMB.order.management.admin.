# utils.py - Utility Functions
import json
from datetime import datetime, timedelta
from config import ist_now, format_ist_datetime
import cloudinary
import cloudinary.api

def generate_map_link(latitude, longitude):
    """Generate Google Maps link from coordinates"""
    if latitude and longitude:
        return f"https://www.google.com/maps?q={latitude},{longitude}"
    return None

def format_currency(amount):
    """Format currency amount"""
    try:
        return f"₹{float(amount):,.2f}"
    except:
        return f"₹0.00"

def get_cloudinary_image_url(public_id, folder=None, transformation=None):
    """Get Cloudinary image URL"""
    try:
        if not public_id or not public_id.startswith('http'):
            # Try to find image in Cloudinary
            if folder:
                search_result = cloudinary.Search()\
                    .expression(f"folder:{folder}")\
                    .sort_by('public_id', 'desc')\
                    .execute()
                
                for resource in search_result.get('resources', []):
                    if public_id in resource['public_id']:
                        return resource['secure_url']
        
        return public_id or "https://res.cloudinary.com/demo/image/upload/v1633427556/default_image.jpg"
    except Exception as e:
        print(f"Cloudinary error: {e}")
        return "https://res.cloudinary.com/demo/image/upload/v1633427556/default_image.jpg"

def get_time_period_dates(period):
    """Get start and end dates for time period"""
    now = ist_now()
    
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'week':
        start_date = now - timedelta(days=7)
        end_date = now
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now
    elif period == 'last_month':
        first_day_last_month = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day_last_month = now.replace(day=1) - timedelta(days=1)
        start_date = first_day_last_month.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = last_day_last_month.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:  # all time
        start_date = datetime.min.replace(tzinfo=now.tzinfo)
        end_date = now
    
    return start_date, end_date

def prepare_chart_data(orders_data, top_items, status_data):
    """Prepare data for Chart.js charts"""
    
    # Orders timeline chart
    timeline_labels = []
    timeline_values = []
    revenue_values = []
    
    for item in orders_data:
        period = item['period']
        if isinstance(period, datetime):
            timeline_labels.append(format_ist_datetime(period, "%d %b %I:%M %p"))
        else:
            timeline_labels.append(str(period))
        
        timeline_values.append(item['order_count'])
        revenue_values.append(float(item['total_revenue'] or 0))
    
    timeline_chart = {
        'labels': timeline_labels,
        'orders': timeline_values,
        'revenue': revenue_values
    }
    
    # Top items chart
    item_labels = []
    item_quantities = []
    item_revenues = []
    
    for item in top_items:
        item_labels.append(item['item_name'][:20] + ('...' if len(item['item_name']) > 20 else ''))
        item_quantities.append(item['total_quantity'])
        item_revenues.append(float(item['total_revenue'] or 0))
    
    items_chart = {
        'labels': item_labels,
        'quantities': item_quantities,
        'revenues': item_revenues
    }
    
    # Status distribution chart
    status_labels = []
    status_values = []
    status_colors = {
        'pending': '#ffc107',
        'confirmed': '#17a2b8',
        'processing': '#007bff',
        'shipped': '#6f42c1',
        'delivered': '#28a745',
        'cancelled': '#dc3545'
    }
    
    for item in status_data:
        status_labels.append(item['status'].title())
        status_values.append(item['count'])
    
    status_chart = {
        'labels': status_labels,
        'values': status_values,
        'colors': [status_colors.get(label.lower(), '#6c757d') for label in status_labels]
    }
    
    return {
        'timeline': timeline_chart,
        'items': items_chart,
        'status': status_chart
    }
