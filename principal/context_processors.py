from .models import Cliente, CarritoCompra, DetalleCarrito

def carrito_context(request):
    if request.user.is_authenticated:
        cliente = Cliente.objects.filter(usuario=request.user.username).first()
        carrito = CarritoCompra.objects.filter(idcliente=cliente, estado = 1).first()
        detalle = DetalleCarrito.objects.filter(idcarrito=carrito) if carrito else []
        total = sum([item.idproducto.precio * item.cantidad for item in detalle])
    else:
        cliente = Cliente.objects.filter(usuario='invitado').first()
        carrito = CarritoCompra.objects.filter(idcliente=cliente, estado = 1).first()
        detalle = DetalleCarrito.objects.filter(idcarrito=carrito) if carrito else []
        total = sum([item.idproducto.precio * item.cantidad for item in detalle])

    return {
        'carrito': detalle,
        'total': total,
    }
