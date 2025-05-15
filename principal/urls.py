from django.urls import path
from . import views
from pagos import views as view

urlpatterns = [
    #path('crear_pago', view.crear_pago, name='crear_pago'),
    path('', views.index, name='index'),
    path('productos/<str:categoria>', views.productos, name='productos'),
    path('unitario/<int:productoID>', views.unitario, name='unitario'),
    path('carrito', views.carrito, name='carrito'),
    path('cuenta', views.cuenta, name='cuenta'),
    path('resumen', views.resumen, name='resumen'),
    path('pago', views.pago, name='pago'),
    path('administrador', views.admin, name='administrador'),
    path('contador', views.contador, name='contador'),
    path('vendedor', views.vendedor, name='vendedor'),
    path('bodeguero', views.bodeguero, name='bodeguero'),

    path('cerrar_sesion', views.cerrar_sesion, name='cerrar_sesion'),

    path('gestionCatalogo', views.gestionCatalogo, name='gestionCatalogo'),
    path('gestionDescuento', views.gestionDescuento, name='gestionDescuento'),
    path('gestionInventario', views.gestionInventario, name='gestionInventario'),
    path('gestionPedidos', views.gestionPedidos, name='gestionPedidos'),
    path('gestionPagos', views.gestionPagos, name='gestionPagos'),
    path('transferencias', views.transferencias, name='transferencias'),
    path('reportesFinancieros', views.reportesFinancieros, name='reportesFinancieros'),
    path('gestionReportesAdmin', views.gestionReportesAdmin, name='gestionReportesAdmin'),
    path('gestionVenta', views.gestionVenta, name='gestionVenta'),
    path('entregaPedidos', views.entregaPedidos, name='entregaPedidos'),
    path('preparacionDespacho', views.preparacionDespacho, name='preparacionDespacho'),
    path('verOrdenes', views.verOrdenes, name='verOrdenes'),
    path('entregasContador', views.entregasContador, name='entregasContador'),

    path('nosotros', views.nosotros, name='nosotros'),
    path('Cambios', views.Cambios, name='Cambios'),
    path('TerminosyCondiciones', views.TerminosyCondiciones, name='TerminosyCondiciones'),
    path('base', views.base, name='base'),
    path('contacto', views.contacto, name='contacto'),
    path('pagos/cancel/', views.webpay_cancel, name='webpay_cancel'),

    path('agregar', views.agregarCarrito, name="agregar"),
    path('carrito/actualizar', views.actualizarCarrito, name='actualizarCarrito'),
    path('borrar/<int:productoID>', views.borrar, name='borrar'),
    path('comprobante/<uuid:pago_id>/', views.generar_comprobante_pdf, name='comprobante'),
    path('comprobante/', views.generar_comprobante, name='generar_comprobante'),
]
