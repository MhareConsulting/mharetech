from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('mytrack/', views.mytrack, name='mytrack'),
    path('myroutes/', views.myroutes, name='myroutes'),
    path('expo/', views.expo_connect, name='expo_connect'),
    path('expo/vcard/', views.expo_vcard, name='expo_vcard'),
    path('expo/submit/', views.expo_submit, name='expo_submit'),
    path('22onsloane/', views.sloane_loop, name='sloane_loop'),
]
