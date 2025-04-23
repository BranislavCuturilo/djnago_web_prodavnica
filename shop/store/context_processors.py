from .models import Cart, CartItem, Wishlist
from django.contrib.auth.decorators import login_required

def cart(request):
    """Add cart information to template context"""
    cart = None
    cart_items = []
    cart_total = 0
    cart_count = 0

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_count = cart_items.count()
        cart_total = sum(item.total_price for item in cart_items)
    else:
        session_key = request.session.session_key
        if session_key:
            cart, created = Cart.objects.get_or_create(session_key=session_key)
            cart_items = cart.items.all()
            cart_count = cart_items.count()
            cart_total = sum(item.total_price for item in cart_items)

    return {
        'cart': cart,
        'cart_items': cart_items,
        'cart_count': cart_count,
        'cart_total': cart_total
    }

def wishlist(request):
    """Add wishlist information to template context"""
    wishlist_items = []
    wishlist_count = 0

    if request.user.is_authenticated:
        wishlist_items = Wishlist.objects.filter(user=request.user)
        wishlist_count = wishlist_items.count()

    return {
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_count
    } 