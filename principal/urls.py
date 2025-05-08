from django.urls import path
from . import views
from pagos import views as view

urlpatterns = [
    #path('crear_pago', view.crear_pago, name='crear_pago'),
    path('', views.index, name='index'),
    path('shop', views.shop, name='shop'),
    path('detail', views.detail, name='detail'),
    path('carrito', views.carrito, name='carrito'),
    path('pagos/cancel/', views.webpay_cancel, name='webpay_cancel'),
]
