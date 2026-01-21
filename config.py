# config.py - Admin Configuration
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Timezone Configuration
IST_TIMEZONE = pytz.timezone('Asia/Kolkata')
UTC_TIMEZONE = pytz.utc

# Database Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "demo")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "demo")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "demo")

# Admin Configuration
ADMIN_SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'dev-admin-secret-key-change-in-production')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Timezone helper functions
def ist_now():
    """Returns current time in IST timezone"""
    try:
        utc_now = datetime.now(UTC_TIMEZONE)
        return utc_now.astimezone(IST_TIMEZONE)
    except Exception:
        return datetime.now()

def to_ist(datetime_obj):
    """Convert any datetime object to IST timezone safely"""
    if datetime_obj is None:
        return None
    
    try:
        # If it's already timezone aware
        if datetime_obj.tzinfo is not None:
            return datetime_obj.astimezone(IST_TIMEZONE)
        
        # If it's naive, assume it's UTC (for existing data)
        return UTC_TIMEZONE.localize(datetime_obj).astimezone(IST_TIMEZONE)
    except Exception:
        return datetime_obj

def format_ist_datetime(datetime_obj, format_str="%d %b %Y, %I:%M %p"):
    """Format datetime in IST with Indian 12-hour AM/PM format"""
    try:
        ist_time = to_ist(datetime_obj)
        if ist_time:
            return ist_time.strftime(format_str)
    except Exception:
        pass
    return ""