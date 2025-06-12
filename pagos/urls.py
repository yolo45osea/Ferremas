from django.urls import path
from . import views

urlpatterns = [
    path('', views.crear_pago, name='crear_pago'),
    path("payments/process/<uuid:token>/", views.process_data, name="process_payment"),
    path('payments/success/<int:pk>/', views.payment_success, name='payment_success'),
    path('payments/failure/<int:pk>/', views.payment_failure, name='payment_failure'),
]
