from django.http import JsonResponse
from django.shortcuts import render
import requests
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from payments import get_payment_model, RedirectNeeded
from payments.core import provider_factory
from django.db.transaction import atomic

import logging
from pagos.models import Payment
from django_payments_chile import WebpayProvider
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Create your views here.
def index(request):
    precio = 10000
    tasa_conversion = 0
    if request.method == "POST":
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

        # Imprimir la respuesta completa para depurar
        print("Respuesta de la API:", response.status_code, response.json())  # Aquí puedes ver toda la respuesta

        if response.status_code == 200:
            data = response.json()
            # Verifica si las tasas están disponibles en la respuesta
            if "conversion_rates" in data:
                tasa = data["conversion_rates"].get(moneda)
                if tasa:
                    #precio = precio * tasa
                    """return JsonResponse({
                        "from": "CLP",
                        "to": moneda,
                        "tasa": tasa
                    })"""
                else:
                    return JsonResponse({"error": "No se encontró la tasa para CLP."}, status=500)
            else:
                return JsonResponse({"error": "No se pudo obtener las tasas de cambio."}, status=500)
        else:
            return JsonResponse({"error": "Error al consultar la API", "details": response.text}, status=500)
    print(f"tasa: {tasa_conversion}, precio: {precio}")
    return render(request, 'index.html', {'precio': precio * tasa_conversion if tasa_conversion>0 else precio})

def shop(request):
    return render(request, 'shop.html')

def detail(request):
    return render(request, 'detail.html')

def carrito(request):
    payment_model = get_payment_model()  # Obtienes el modelo de pago de django-payments

    if request.method == 'POST':
        monto = request.POST.get('valor')
        try:
            # Crear un objeto de pago
            payment = payment_model.objects.create(
                variant="webpay",  # Debe coincidir con el nombre configurado en PAYMENT_VARIANTS
                description="Pago por Orden #123",
                total=monto,  # Monto en centavos (10000 = 100 pesos)
                currency="CLP",
                billing_first_name="Juan",
                billing_last_name="Pérez",
                billing_email="juan.perez@example.com",
            )

            # Obtener el formulario que hace POST automáticamente a Webpay
            form = payment.get_form()
            

            # Mostrar el formulario para que el navegador lo envíe automáticamente a Webpay
            return render(request, 'redirigir_webpay.html', {'form': form})

        except RedirectNeeded as redirect_to:
            return redirect(str(redirect_to))
        except Exception as e:
            logger.error(f"Error al crear pago: {str(e)}")
            return HttpResponse(f"Hubo un error: {str(e)}")
    return render(request, 'cart.html')