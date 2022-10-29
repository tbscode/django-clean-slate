import django.contrib.auth.password_validation as pw_validation
from datetime import datetime
from django.conf import settings
from django.core import exceptions
from django.utils.module_loading import import_string
from rest_framework.decorators import api_view, schema, throttle_classes, permission_classes
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie, vary_on_headers
from rest_framework import serializers
from rest_framework.throttling import UserRateThrottle
from rest_framework.permissions import IsAuthenticated
from .models import ProfileSerializer, UserSerializer
from django.contrib.auth import get_user_model


class Throttle200TimesPerDay(UserRateThrottle):
    rate = '200/day'


@throttle_classes([Throttle200TimesPerDay])
@vary_on_headers("Authorization",)
# TODO: invalidate chache whenever user state changes e.g.: new match
@cache_page(60*60*2)
# Waithin on 'async' support for DRF: https://github.com/encode/django-rest-framework/discussions/7774
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_app_data(request):
    """
    Returns the main application data for a given user.
    Basicly this is the data the main frontend app receives
    """
    return Response({
        "self": {
            "info": "self info",
            "profile": "profile",
            "state": "state"
        },
        "matches": [{
            "info": "some info placeholder",
            "profile": "some profile placeholder"
        }],
    })


class RegistrationData:
    def __init__(self, email, first_name, second_name, password):
        self.email = email
        self.first_name = first_name
        self.second_name = second_name
        self.password = password


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=150)
    second_name = serializers.CharField(max_length=150)
    password1 = serializers.CharField(max_length=100)
    password2 = serializers.CharField(max_length=100)

    def create(self, validated_data):
        # Password same validation happens in 'validate()' we need only one password now
        return RegistrationData(
            **{k: v for k, v in validated_data.items() if k not in ["password1", "password2"]},
            password=validated_data['password1'])

    def validate(self, data):
        user = get_user_model()(
            username=data['email'],
            email=data['email'],
            first_name=data['first_name']
        )
        extra_errors = dict()
        try:
            pw_validation.validate_password(
                password=data['password1'], user=user)
        # the exception raised here is different than serializers.ValidationError
        except exceptions.ValidationError as e:
            extra_errors['password1'] = list(e.messages)
        if data['password1'] != data['password2']:
            extra_errors.setdefault("password1", []).append(
                "Passwords not matching")
        return super(RegistrationSerializer, self).validate(data)


@api_view(['POST'])
def register(request):
    """
    Register any user
    e.g.:
    curl --data "first_name=tim&second_name=schupp&email=test@gmail.com&password1=was&password2=was" http://localhost:8000/api/v1/register/
    """
    serializer = RegistrationSerializer(data=request.data)
    if serializer.is_valid():
        # Perform registration, send email etc...
        # The types are secure, we checked that using the 'Registration Serializer'
        registration_data = serializer.save()
        user_data_serializer = UserSerializer(
            # Currently we don't allow any specific username
            username=registration_data.email,
            email=registration_data.email,
            first_name=registration_data.first_name,
            second_name=registration_data.second_name,
            password=registration_data.password
        )
        if user_data_serializer.is_valid():
            get_user_model().objects.create(**user_data_serializer.data)
        return Response("Sucessfully Created User")
    else:
        return Response(serializer.errors)
