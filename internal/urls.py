from django.urls import path

from . import views

urlpatterns = [
    path('', views.hub, name='internal_hub'),
    path('login/', views.login_view, name='internal_login'),
    path('logout/', views.logout_view, name='internal_logout'),
    path('assessment/', views.assessment, name='internal_assessment'),
    path('assessment/submit/', views.assessment_submit, name='internal_assessment_submit'),
    path('pricing/', views.pricing, name='internal_pricing'),
    path('downloads/', views.downloads, name='internal_downloads'),
]
