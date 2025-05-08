from django.urls import path
from . import views
from pagos import views as view

urlpatterns = [
    #path('crear_pago', view.crear_pago, name='crear_pago'),
    path('', views.index, name='index'),
    path('productos/<str:categoria>', views.productos, name='productos'),
    path('detail', views.detail, name='detail'),
    path('carrito', views.carrito, name='carrito'),
    path('cuenta', views.cuenta, name='cuenta'),
    path('resumen', views.resumen, name='resumen'),
    path('pago', views.pago, name='pago'),
    path('admininstrador', views.admin, name='admininstrador'),
    path('contador', views.contador, name='contador'),
    path('pagos/cancel/', views.webpay_cancel, name='webpay_cancel'),
]
