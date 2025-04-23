from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model



class CustomerManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email je obavezan'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Customer(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    name = models.CharField(max_length=255, verbose_name="Ime", blank=True)
    phone = models.CharField(max_length=15, verbose_name="Telefon", blank=True)
    age = models.IntegerField(verbose_name="Godine", null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[
        ('male', 'Muški'),
        ('female', 'Ženski'),
    ], verbose_name="Pol", null=True, blank=True)
    address = models.CharField(max_length=255, verbose_name="Adresa", blank=True)
    country = models.CharField(max_length=255, verbose_name="Drzava", blank=True)
    city = models.CharField(max_length=255, verbose_name="Grad", blank=True)
    zip_code = models.CharField(max_length=255, verbose_name="Poštanski broj", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomerManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _('Korisnik')
        verbose_name_plural = _('Korisnici')

class ChangeHistory(models.Model):
    ACTION_CHOICES = [
        ('create', 'Kreiranje'),
        ('update', 'Ažuriranje'),
        ('delete', 'Brisanje'),
    ]

    user = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, verbose_name="Korisnik")
    model_name = models.CharField(max_length=100, verbose_name="Model")
    object_id = models.PositiveIntegerField(verbose_name="ID objekta")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="Akcija")
    changes = models.JSONField(verbose_name="Promene")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Datum promene")

    class Meta:
        verbose_name = "Istorija promena"
        verbose_name_plural = "Istorija promena"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} - {self.model_name} ({self.object_id})"

class Brand(models.Model):
    name = models.CharField(max_length=255, verbose_name="Naziv brenda")
    description = models.TextField(verbose_name="Opis brenda", null=True, blank=True)
    logo = models.ImageField(upload_to='brands/logos/', null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Brend"
        verbose_name_plural = "Brendovi"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_instance = None if is_new else Brand.objects.get(pk=self.pk)
        super().save(*args, **kwargs)
        
        changes = {}
        if not is_new:
            for field in self._meta.fields:
                old_value = getattr(old_instance, field.name)
                new_value = getattr(self, field.name)
                if old_value != new_value:
                    changes[field.name] = {
                        'old': str(old_value),
                        'new': str(new_value)
                    }
        
        ChangeHistory.objects.create(
            user=self._get_current_user(),
            model_name='Brand',
            object_id=self.pk,
            action='create' if is_new else 'update',
            changes=changes
        )

    def delete(self, *args, **kwargs):
        ChangeHistory.objects.create(
            user=self._get_current_user(),
            model_name='Brand',
            object_id=self.pk,
            action='delete',
            changes={}
        )
        super().delete(*args, **kwargs)

    def _get_current_user(self):
        from django.contrib.auth import get_user
        from django.contrib.auth.middleware import get_user
        from django.utils.functional import SimpleLazyObject
        from django.conf import settings
        
        if not hasattr(self, '_request'):
            return None
            
        if not hasattr(self._request, 'user'):
            return None
            
        user = self._request.user
        if isinstance(user, SimpleLazyObject):
            user = user._wrapped
            
        return user if user.is_authenticated else None

class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name="Naziv kategorije")
    description = models.TextField(verbose_name="Opis kategorije", null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Gender flags - a category can be for multiple genders
    is_male = models.BooleanField(default=False, verbose_name="Muški")
    is_female = models.BooleanField(default=False, verbose_name="Ženski")
    is_children = models.BooleanField(default=False, verbose_name="Deca")
    
    # Ordering
    order = models.PositiveIntegerField(default=0, verbose_name="Redosled")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kategorija"
        verbose_name_plural = "Kategorije"
        ordering = ['order', 'name']

    def get_gender_display(self):
        genders = []
        if self.is_male:
            genders.append("Muški")
        if self.is_female:
            genders.append("Ženski")
        if self.is_children:
            genders.append("Deca")
        return ", ".join(genders) if genders else "Unisex"

class Tag(models.Model):
    name = models.CharField(max_length=255, verbose_name="Naziv taga")
    description = models.TextField(verbose_name="Opis taga", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tagovi"

class Product(models.Model):
    # Basic Information
    name = models.CharField(max_length=200, verbose_name="Naziv proizvoda")
    short_description = models.TextField(verbose_name="Kratki opis proizvoda", null=True, blank=True)
    description = models.TextField(verbose_name="Opis proizvoda", null=True, blank=True)
    sku = models.CharField(max_length=255, verbose_name="Šifra proizvoda", unique=True)
    
    # Main Image
    main_image = models.ImageField(upload_to='products/main/', verbose_name="Glavna slika")
    hover_image = models.ImageField(upload_to='products/hover/', verbose_name="Hover slika", null=True, blank=True)
    
    # Pricing
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Cena"
    )
    discount = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Popust (%)"
    )
    currency = models.CharField(max_length=3, default='RSD', verbose_name="Valuta")
    tax_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        verbose_name="Stopa poreza"
    )
    is_taxable = models.BooleanField(default=True, verbose_name="Obračunati porez")
    shipping_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Cena dostave"
    )
    is_shipping_free = models.BooleanField(default=False, verbose_name="Dostava je besplatna")
    is_shipping_required = models.BooleanField(default=True, verbose_name="Dostava je obavezna")

    # Stock & Inventory
    stock = models.PositiveIntegerField(default=0, verbose_name="Količina na stanju")
    min_amount = models.IntegerField(default=1, verbose_name="Minimalna količina")
    max_amount = models.IntegerField(default=0, verbose_name="Maksimalna količina")
    is_digital = models.BooleanField(default=False, verbose_name="Digitalni proizvod")
    digital_file = models.FileField(upload_to='products/digital/', null=True, blank=True)

    # Categorization
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    sub_category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_category')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    
    # Product Type Flags
    is_featured = models.BooleanField(default=False, verbose_name="Featured proizvod")
    is_new = models.BooleanField(default=False, verbose_name="Novi proizvod")
    is_best_seller = models.BooleanField(default=False, verbose_name="Best seller proizvod")
    is_top_rated = models.BooleanField(default=False, verbose_name="Top rated proizvod")
    is_on_sale = models.BooleanField(default=False, verbose_name="Na popustu")
    
    # Target Audience
    is_male = models.BooleanField(default=False, verbose_name="Muški proizvod")
    is_female = models.BooleanField(default=False, verbose_name="Ženski proizvod")
    is_children = models.BooleanField(default=False, verbose_name="Dječji proizvod")
    min_age = models.IntegerField(null=True, blank=True, verbose_name="Minimalna dob")
    max_age = models.IntegerField(null=True, blank=True, verbose_name="Maksimalna dob")

    # Physical Attributes
    weight = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Težina"
    )
    dimensions = models.CharField(max_length=255, null=True, blank=True, verbose_name="Dimenzije")
    material = models.CharField(max_length=255, null=True, blank=True, verbose_name="Materijal")
    color = models.CharField(max_length=255, null=True, blank=True, verbose_name="Boja")
    size = models.CharField(max_length=255, null=True, blank=True, verbose_name="Veličina")
    
    # Production Information
    made_in = models.CharField(max_length=255, null=True, blank=True, verbose_name="Proizvedeno u")
    made_in_country = models.CharField(max_length=255, null=True, blank=True, verbose_name="Država proizvodnje")
    made_in_city = models.CharField(max_length=255, null=True, blank=True, verbose_name="Grad proizvodnje")
    
    # Product Codes
    ean = models.CharField(max_length=255, null=True, blank=True, verbose_name="EAN")
    isbn = models.CharField(max_length=255, null=True, blank=True, verbose_name="ISBN")
    upc = models.CharField(max_length=255, null=True, blank=True, verbose_name="UPC")
    gtin = models.CharField(max_length=255, null=True, blank=True, verbose_name="GTIN")
    mpn = models.CharField(max_length=255, null=True, blank=True, verbose_name="MPN")
    
    # Product Attributes
    is_eco = models.BooleanField(default=False, verbose_name="Ekološki proizvod")
    is_organic = models.BooleanField(default=False, verbose_name="Organski proizvod")
    is_vegan = models.BooleanField(default=False, verbose_name="Vegan proizvod")
    is_gluten_free = models.BooleanField(default=False, verbose_name="Bez glutena")
    is_dairy_free = models.BooleanField(default=False, verbose_name="Bez mleka")
    is_sugar_free = models.BooleanField(default=False, verbose_name="Bez šećera")
    
    # SEO
    seo_title = models.CharField(max_length=255, null=True, blank=True, verbose_name="SEO naslov")
    seo_description = models.TextField(null=True, blank=True, verbose_name="SEO opis")
    seo_keywords = models.TextField(null=True, blank=True, verbose_name="SEO ključne reči")
    seo_image = models.ImageField(upload_to='products/seo/', null=True, blank=True, verbose_name="SEO slika")
    
    # Statistics
    num_views = models.IntegerField(default=0, verbose_name="Broj pregleda")
    num_purchases = models.IntegerField(default=0, verbose_name="Broj kupnji")
    num_wishlist = models.IntegerField(default=0, verbose_name="Broj želja")
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Proizvod"
        verbose_name_plural = "Proizvodi"
        ordering = ['-created_at']

    @property
    def discounted_price(self):
        if self.discount:
            return self.price * (1 - Decimal(self.discount) / 100)
        return self.price

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_instance = None if is_new else Product.objects.get(pk=self.pk)
        super().save(*args, **kwargs)
        
        changes = {}
        if not is_new:
            for field in self._meta.fields:
                old_value = getattr(old_instance, field.name)
                new_value = getattr(self, field.name)
                if old_value != new_value:
                    changes[field.name] = {
                        'old': str(old_value),
                        'new': str(new_value)
                    }
        
        ChangeHistory.objects.create(
            user=self._get_current_user(),
            model_name='Product',
            object_id=self.pk,
            action='create' if is_new else 'update',
            changes=changes
        )

    def delete(self, *args, **kwargs):
        ChangeHistory.objects.create(
            user=self._get_current_user(),
            model_name='Product',
            object_id=self.pk,
            action='delete',
            changes={}
        )
        super().delete(*args, **kwargs)

    def _get_current_user(self):
        from django.contrib.auth import get_user
        from django.contrib.auth.middleware import get_user
        from django.utils.functional import SimpleLazyObject
        from django.conf import settings
        
        if not hasattr(self, '_request'):
            return None
            
        if not hasattr(self._request, 'user'):
            return None
            
        user = self._request.user
        if isinstance(user, SimpleLazyObject):
            user = user._wrapped
            
        return user if user.is_authenticated else None

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='products/gallery/')
    is_main = models.BooleanField(default=False)
    is_hover = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    alt_text = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Slika proizvoda"
        verbose_name_plural = "Slike proizvoda"

    def __str__(self):
        return f"Slika za {self.product.name}"

class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=255, null=True, blank=True)
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.id)
    
    
class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    size = models.CharField(max_length=255, null=True, blank=True)
    color = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_shipping = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)


    def __str__(self):
        return str(self.id)
    

class ShippingAddress(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    zipcode = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)



class Cart(models.Model):
    user = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Korpa"
        verbose_name_plural = "Korpe"

    def __str__(self):
        if self.user:
            return f"Korpa korisnika {self.user.email}"
        return f"Korpa sesije {self.session_key}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stavka korpe"
        verbose_name_plural = "Stavke korpe"
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        return self.quantity * self.product.discounted_price

class Wishlist(models.Model):
    user = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lista želja"
        verbose_name_plural = "Liste želja"
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"

class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=255)
    value = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Specifikacija proizvoda"
        verbose_name_plural = "Specifikacije proizvoda"

class ProductFAQ(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "FAQ proizvoda"
        verbose_name_plural = "FAQ proizvoda"

class ProductReview(models.Model):
    RATING_CHOICES = [
        (1, '1 Zvezda'),
        (2, '2 Zvezde'),
        (3, '3 Zvezde'),
        (4, '4 Zvezde'),
        (5, '5 Zvezda'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(Customer, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Recenzija proizvoda"
        verbose_name_plural = "Recenzije proizvoda"
        ordering = ['-created_at']

class UTMTracking(models.Model):
    user = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True)  # For anonymous users
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    utm_term = models.CharField(max_length=100, blank=True)
    utm_content = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    converted = models.BooleanField(default=False)  # Whether conversion occurred
    last_activity = models.DateTimeField(auto_now=True)  # Track last activity

    def __str__(self):
        return f"UTM: {self.utm_source} - {self.utm_campaign}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'UTM Tracking'
        verbose_name_plural = 'UTM Trackings'

class Bundle(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    products = models.ManyToManyField(Product, related_name='bundles')
    required_quantity = models.PositiveIntegerField(default=2)
    bundle_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return self.name

    @property
    def discount_percentage(self):
        total_original_price = sum(product.price for product in self.products.all())
        return round((1 - self.bundle_price / total_original_price) * 100)

class Promotion(models.Model):
    PROMOTION_TYPES = [
        ('BUY_X_GET_Y_FREE', 'Buy X Get Y Free'),
        ('BUY_X_GET_Y_DISCOUNT', 'Buy X Get Y Discount'),
        ('CATEGORY_DISCOUNT', 'Category Discount'),
        ('TAG_DISCOUNT', 'Tag Discount'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    promotion_type = models.CharField(max_length=50, choices=PROMOTION_TYPES)
    required_quantity = models.PositiveIntegerField(default=2)
    discount_percentage = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    categories = models.ManyToManyField(Category, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    def __str__(self):
        return self.name

class Collection(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField(Product, related_name='collections')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.start_date.year})"

    class Meta:
        verbose_name = "Kolekcija"
        verbose_name_plural = "Kolekcije"
        ordering = ['-start_date']

class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True, verbose_name="Email")
    is_active = models.BooleanField(default=True, verbose_name="Aktivna pretplata")
    subscribed_at = models.DateTimeField(auto_now_add=True, verbose_name="Datum pretplate")
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name="Datum odjave")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Newsletter pretplata"
        verbose_name_plural = "Newsletter pretplate"
        ordering = ['-subscribed_at']

    def __str__(self):
        return self.email
