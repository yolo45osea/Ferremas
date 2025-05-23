from django.http import JsonResponse
import requests
from .models import Cliente, CarritoCompra, DetalleCarrito

def carrito_context(request):
    tasa_conversion = 0
    if request.user.is_authenticated:
        cliente = Cliente.objects.filter(usuario=request.user.username).first()
        carrito = CarritoCompra.objects.filter(idcliente=cliente, estado = 1).first()
        detalle = DetalleCarrito.objects.filter(idcarrito=carrito)
        total = sum([item.idproducto.precio * item.cantidad for item in detalle])
    else:
        session_key = request.session.session_key
        carrito = CarritoCompra.objects.filter(session_key=session_key, estado = 1).first()
        detalle = DetalleCarrito.objects.filter(idcarrito=carrito)
        total = sum([item.idproducto.precio * item.cantidad for item in detalle])

        tasa_conversion = 0
        moneda = 'CLP'

        if request == 'POST':

            moneda = request.POST.get("moneda", "USD").upper()
            moneda_local = 'CLP'
            montos = request.POST.get('monto')

            # Asegurarse de que la moneda es válida
            monedas_validas = ["USD", "EUR", "CAD", "CLP"]
            if moneda not in monedas_validas:
                return JsonResponse({"error": "Moneda no válida"}, status=400)

            # Obtener la tasa de cambio usando Exchangerate-API
            api_key = "e62c5a2d52f4a1d6b195a3b8"  # Reemplaza con tu clave de API
            url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{moneda_local}"

            response = requests.get(url)

            
            data = response.json()
            tasa = data["conversion_rates"].get(moneda)
            tasa_conversion = tasa
            print(f'tasa: {tasa_conversion}')
            

    return {
        'carrito': detalle,
        'total': total,
        'tasa': tasa_conversion
    }
