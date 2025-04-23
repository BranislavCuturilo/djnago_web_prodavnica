from urllib.parse import urlencode
from django.conf import settings
from .models import UTMTracking, Customer, Cart, CartItem
from django.contrib.sessions.models import Session

def generate_utm_url(base_url, source, medium, campaign, term=None, content=None):
    """
    Generate a URL with UTM parameters
    """
    params = {
        'utm_source': source,
        'utm_medium': medium,
        'utm_campaign': campaign,
    }
    
    if term:
        params['utm_term'] = term
    if content:
        params['utm_content'] = content
        
    return f"{base_url}?{urlencode(params)}"

def track_conversion(user=None, session_key=None):
    """
    Mark a UTM tracking record as converted
    """
    if user:
        utm_data = UTMTracking.objects.filter(user=user).last()
    elif session_key:
        utm_data = UTMTracking.objects.filter(session_key=session_key).last()
    else:
        return None
        
    if utm_data:
        utm_data.converted = True
        utm_data.save()
    return utm_data

def get_utm_data(request):
    """
    Get UTM data from session or create new tracking
    """
    utm_data = request.session.get('utm_data', {})
    if not utm_data and request.user.is_authenticated:
        utm_tracking = UTMTracking.objects.filter(user=request.user).last()
        if utm_tracking:
            utm_data = {
                'source': utm_tracking.utm_source,
                'medium': utm_tracking.utm_medium,
                'campaign': utm_tracking.utm_campaign,
                'term': utm_tracking.utm_term,
                'content': utm_tracking.utm_content,
            }
            request.session['utm_data'] = utm_data
    return utm_data 

def get_or_create_cart(request):
    """
    Get or create a cart for the current user/session.
    For authenticated users, returns their user cart.
    For anonymous users, returns a session-based cart.
    """
    if request.user.is_authenticated:
        # For authenticated users, get or create a user-based cart
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # For anonymous users, get or create a session-based cart
        session_key = request.session.session_key
        if not session_key:
            request.session.save()
            session_key = request.session.session_key
            
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    
    return cart

def get_cart_items_count(cart):
    """Get the total number of items in the cart"""
    return CartItem.objects.filter(cart=cart).count()

def get_cart_total(cart):
    """Calculate the total price of all items in the cart"""
    cart_items = CartItem.objects.filter(cart=cart)
    return sum(item.total_price for item in cart_items) 