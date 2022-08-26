from django.urls import path

from casdoor_auth import views

urlpatterns = [
    path('login/', views.toLogin, name='casdoor_sso'),
    path('callback/', views.callback, name='callback'),
]
