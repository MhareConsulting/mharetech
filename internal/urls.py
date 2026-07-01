from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='internal_home'),
    path('login/', views.login_view, name='internal_login'),
    path('logout/', views.logout_view, name='internal_logout'),
    path('quote.pdf', views.quote_pdf, name='internal_quote_pdf'),

    path('<slug:product>/', views.toolkit, name='internal_toolkit'),
    path('<slug:product>/assessment/', views.assessment, name='internal_assessment'),
    path('<slug:product>/assessment/submit/', views.assessment_submit, name='internal_assessment_submit'),
    path('<slug:product>/pricing/', views.pricing, name='internal_pricing'),
    path('<slug:product>/downloads/', views.downloads, name='internal_downloads'),
]
