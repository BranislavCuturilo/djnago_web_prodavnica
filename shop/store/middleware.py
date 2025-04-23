from django.utils.deprecation import MiddlewareMixin
from .models import UTMTracking, Customer

class UTMTrackingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Check if we have UTM parameters
        utm_params = {
            'utm_source': request.GET.get('utm_source'),
            'utm_medium': request.GET.get('utm_medium'),
            'utm_campaign': request.GET.get('utm_campaign'),
            'utm_term': request.GET.get('utm_term'),
            'utm_content': request.GET.get('utm_content'),
        }

        # Only proceed if we have at least one UTM parameter
        if any(utm_params.values()):
            # Get or create session key
            if not request.session.session_key:
                request.session.create()
            
            # Update or create UTM tracking record
            utm_data, created = UTMTracking.objects.update_or_create(
                session_key=request.session.session_key,
                defaults=utm_params
            )

            # If user is authenticated, link to their account
            if request.user.is_authenticated:
                utm_data.user = request.user
                utm_data.save()

            # Store UTM data in session for later use
            request.session['utm_data'] = {
                'source': utm_params['utm_source'],
                'medium': utm_params['utm_medium'],
                'campaign': utm_params['utm_campaign'],
                'term': utm_params['utm_term'],
                'content': utm_params['utm_content'],
            } 