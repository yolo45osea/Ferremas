from django.urls import path
from . import views

urlpatterns = [
    path('', views.crear_pago, name='crear_pago'),
    path("payments/process/<uuid:token>/", views.process_data, name="process_payment"),
    path('payments/success/<uuid:pk>/', views.payment_success, name='payment_success'),
    path('payments/failure/<uuid:pk>/', views.payment_failure, name='payment_failure'),
]
