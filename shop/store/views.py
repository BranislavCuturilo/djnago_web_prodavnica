from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from .models import (
    Product, Cart, CartItem, Wishlist, Customer, Category, Order, 
    Bundle, Promotion, Collection, NewsletterSubscription
)
from django.views.decorators.http import require_POST
import json
from .utils import get_or_create_cart
from .forms import CustomerRegistrationForm, CustomerLoginForm, CustomerUpdateForm
from django.utils import timezone
from django.db.models import Sum

# Create your views here.
def store(request):
    # Get all active products
    products = Product.objects.filter(is_active=True)
    
    # Get categories for navbar
    male_categories = Category.objects.filter(is_male=True, is_active=True)
    female_categories = Category.objects.filter(is_female=True, is_active=True)
    children_categories = Category.objects.filter(is_children=True, is_active=True)
    
    # Get active collections
    collections = Collection.objects.filter(
        is_active=True,
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    )
    
    # Filter by category if specified
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Filter by collection if specified
    collection_id = request.GET.get('collection')
    if collection_id:
        products = products.filter(collections__id=collection_id)
    
    # Filter by discount if specified
    if request.GET.get('discount') == 'true':
        products = products.filter(discount__gt=0)
    
    # Filter by bundle if specified
    if request.GET.get('bundle') == 'true':
        products = products.filter(bundles__is_active=True)
    
    # Filter by promotion if specified
    if request.GET.get('promotion') == 'true':
        products = products.filter(promotions__is_active=True)
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Sorting
    sort_by = request.GET.get('sort')
    if sort_by == 'price-low':
        products = products.order_by('price')
    elif sort_by == 'price-high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    
    context = {
        'products': products,
        'male_categories': male_categories,
        'female_categories': female_categories,
        'children_categories': children_categories,
        'collections': collections,
    }
    return render(request, 'store/store.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    related_products = Product.objects.filter(
        is_active=True
    ).exclude(id=product_id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'store/product_detail.html', context)

@require_POST
def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    return JsonResponse({
        'status': 'success',
        'message': 'Proizvod dodat u korpu',
        'cart_count': cart.items.count()
    })

@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return JsonResponse({
        'status': 'success',
        'message': 'Proizvod uklonjen iz korpe'
    })

def cart(request):
    cart = get_or_create_cart(request)
    items = cart.items.all()
    
    # Get active bundles and promotions
    active_bundles = Bundle.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    )
    
    active_promotions = Promotion.objects.filter(
        is_active=True,
        start_date__lte=timezone.now(),
        end_date__gte=timezone.now()
    )
    
    # Calculate bundle discounts
    bundle_discounts = []
    for bundle in active_bundles:
        bundle_products = items.filter(product__in=bundle.products.all())
        if bundle_products.count() >= bundle.required_quantity:
            original_price = sum(item.total_price for item in bundle_products)
            discount = original_price - bundle.bundle_price
            bundle_discounts.append({
                'name': bundle.name,
                'discount': discount,
                'products': bundle_products
            })
    
    # Calculate promotion discounts
    promotion_discounts = []
    for promotion in active_promotions:
        if promotion.promotion_type == 'CATEGORY_DISCOUNT':
            category_items = items.filter(product__category__in=promotion.categories.all())
            if category_items.count() >= promotion.required_quantity:
                discount = sum(item.total_price * promotion.discount_percentage / 100 for item in category_items)
                promotion_discounts.append({
                    'name': promotion.name,
                    'discount': discount,
                    'products': category_items
                })
        elif promotion.promotion_type == 'TAG_DISCOUNT':
            tag_items = items.filter(product__tags__in=promotion.tags.all())
            if tag_items.count() >= promotion.required_quantity:
                discount = sum(item.total_price * promotion.discount_percentage / 100 for item in tag_items)
                promotion_discounts.append({
                    'name': promotion.name,
                    'discount': discount,
                    'products': tag_items
                })
    
    total_discount = sum(d['discount'] for d in bundle_discounts) + sum(d['discount'] for d in promotion_discounts)
    subtotal = sum(item.total_price for item in items)
    total = subtotal - total_discount
    
    context = {
        'items': items,
        'subtotal': subtotal,
        'total': total,
        'bundle_discounts': bundle_discounts,
        'promotion_discounts': promotion_discounts,
        'total_discount': total_discount
    }
    return render(request, 'store/cart.html', context)

@login_required
def wishlist_view(request):
    """View for displaying user's wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'store/wishlist.html', {
        'wishlist_items': wishlist_items
    })

@require_POST
@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        return JsonResponse({'status': 'success', 'message': 'Proizvod dodat u listu želja'})
    else:
        return JsonResponse({'status': 'info', 'message': 'Proizvod već postoji u listi želja'})

@require_POST
@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    return JsonResponse({'status': 'success', 'message': 'Proizvod uklonjen iz liste želja'})

@require_POST
def update_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        
        cart = get_or_create_cart(request)
        product = get_object_or_404(Product, id=product_id)
        
        if quantity > 0:
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity, 'price': product.discounted_price}
            )
            if not created:
                cart_item.quantity = quantity
                cart_item.save()
        else:
            CartItem.objects.filter(cart=cart, product=product).delete()
        
        # Recalculate total with bundles and promotions
        items = cart.items.all()
        subtotal = sum(item.total_price for item in items)
        
        # Calculate bundle discounts
        total_bundle_discount = 0
        for bundle in Bundle.objects.filter(is_active=True):
            bundle_products = items.filter(product__in=bundle.products.all())
            if bundle_products.count() >= bundle.required_quantity:
                original_price = sum(item.total_price for item in bundle_products)
                total_bundle_discount += original_price - bundle.bundle_price
        
        # Calculate promotion discounts
        total_promotion_discount = 0
        for promotion in Promotion.objects.filter(is_active=True):
            if promotion.promotion_type == 'CATEGORY_DISCOUNT':
                category_items = items.filter(product__category__in=promotion.categories.all())
                if category_items.count() >= promotion.required_quantity:
                    total_promotion_discount += sum(item.total_price * promotion.discount_percentage / 100 for item in category_items)
            elif promotion.promotion_type == 'TAG_DISCOUNT':
                tag_items = items.filter(product__tags__in=promotion.tags.all())
                if tag_items.count() >= promotion.required_quantity:
                    total_promotion_discount += sum(item.total_price * promotion.discount_percentage / 100 for item in tag_items)
        
        total = subtotal - total_bundle_discount - total_promotion_discount
        
        return JsonResponse({
            'success': True,
            'subtotal': str(subtotal),
            'total': str(total),
            'bundle_discount': str(total_bundle_discount),
            'promotion_discount': str(total_promotion_discount)
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def checkout(request):
    cart = get_or_create_cart(request)
    if not cart.items.exists():
        return redirect('store')
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
        'total_price': sum(item.total_price for item in cart.items.all())
    }
    return render(request, 'store/checkout.html', context)

def register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _('Registration successful! Welcome to our store.'))
            return redirect('store:store')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'account/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = CustomerLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, _('Welcome back!'))
            return redirect('store:store')
    else:
        form = CustomerLoginForm()
    
    return render(request, 'account/login.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    messages.info(request, _('You have been logged out.'))
    return redirect('store:store')

def password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('store:password_reset_done')
    else:
        form = PasswordResetForm()
    
    return render(request, 'account/password_reset.html', {'form': form})

@login_required
def profile(request):
    """View for displaying and updating user profile"""
    if request.method == 'POST':
        form = CustomerUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vaš profil je uspešno ažuriran.')
            return redirect('store:profile')
    else:
        form = CustomerUpdateForm(instance=request.user)
    
    context = {
        'form': form,
        'orders': Order.objects.filter(customer=request.user).order_by('-date_ordered'),
        'is_staff': request.user.is_staff
    }
    return render(request, 'account/profile.html', context)

@login_required
def orders(request):
    """View for displaying user's orders"""
    orders = Order.objects.filter(customer=request.user).order_by('-date_ordered')
    return render(request, 'account/orders.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    """View for displaying order details"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'account/order_detail.html', {'order': order})


def contact(request):
    return render(request, 'store/contact.html')


def about(request):
    return render(request, 'store/about_us.html')

@require_POST
def subscribe_newsletter(request):
    email = request.POST.get('email')
    if not email:
        return JsonResponse({'status': 'error', 'message': 'Email je obavezan'})
    
    try:
        subscription, created = NewsletterSubscription.objects.get_or_create(
            email=email,
            defaults={'is_active': True}
        )
        
        if not created and not subscription.is_active:
            subscription.is_active = True
            subscription.unsubscribed_at = None
            subscription.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Uspešno ste se prijavili na newsletter'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'Došlo je do greške prilikom prijave'
        })


