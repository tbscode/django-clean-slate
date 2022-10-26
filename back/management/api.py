from rest_framework.decorators import api_view, schema, throttle_classes
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie, vary_on_headers
from rest_framework.throttling import UserRateThrottle


class Throttle200TimesPerDay(UserRateThrottle):
    rate = '2000/day'


@api_view(['GET'])
@throttle_classes(Throttle200TimesPerDay)
@method_decorator(cache_page(60*60*2))
@method_decorator(vary_on_headers("Authorization",))
def user_app_data(request):
    """
    Returns the main application data for a given user
    """
    return Response({
        "self": [],
        "matches": [{
            "info": "some info placeholder",
            "profile": "some profile placeholder"
        }],
    })
