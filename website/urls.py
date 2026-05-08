from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('mytrack/', views.mytrack, name='mytrack'),
    path('myroutes/', views.myroutes, name='myroutes'),
]
