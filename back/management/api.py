from rest_framework.decorators import api_view, schema, throttle_classes
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie, vary_on_headers
from rest_framework.throttling import UserRateThrottle


class Throttle200TimesPerDay(UserRateThrottle):
    rate = '2000/day'


@throttle_classes([Throttle200TimesPerDay])
@api_view(['GET'])
@vary_on_headers("Authorization",)
# TODO: invalidate chache whenever user state changes e.g.: new match
@cache_page(60*60*2)
def user_app_data(request):
    """
    Returns the main application data for a given user
    """
    return Response({
        "self": {
            "info": "self info",
            "profile": "profile"
        },
        "matches": [{
            "info": "some info placeholder",
            "profile": "some profile placeholder"
        }],
    })
