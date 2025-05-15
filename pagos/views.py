from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from payments import get_payment_model, RedirectNeeded
from payments.core import provider_factory
from django.db.transaction import atomic

import logging
from pagos.models import Payment
from django_payments_chile import WebpayProvider
from django.views.decorators.csrf import csrf_exempt

from principal.models import CarritoCompra, Cliente, DetalleCarrito, Inventario, Pago

logger = logging.getLogger(__name__)

def crear_pago(request):
    payment_model = get_payment_model()  # Obtienes el modelo de pago de django-payments

    if request.method == 'POST':
        try:
            # Crear un objeto de pago
            payment = payment_model.objects.create(
                variant="webpay",  # Debe coincidir con el nombre configurado en PAYMENT_VARIANTS
                description="Pago por Orden #123",
                total=10000,  # Monto en centavos (10000 = 100 pesos)
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

    return render(request, 'index.html')



@csrf_exempt
@atomic
def process_data(request, token, provider=None):
    """
    Calls process_data of an appropriate provider.

    Raises Http404 if variant does not exist.
    """
    Payment = get_payment_model()
    payment = get_object_or_404(Payment, token=token)

    if 'TBK_TOKEN' in request.GET and 'token_ws' not in request.GET:
        payment.status = 'rejected'  # o 'cancelled'
        payment.save()
        return render(request, 'index.html', {"payment": payment})
        
    if not provider:
        try:
            provider = provider_factory(payment.variant, payment)
        except ValueError as e:
            raise Http404("No such payment") from e

    try:
        # Proceso de la respuesta de Webpay
        response = provider.process_data(payment, request)
        
        # Aquí puedes actualizar el estado según el resultado de Webpay
        # Suponiendo que 'payment' tiene un campo 'status' y que Webpay devuelve un resultado en 'response'
        
        if response.get("estado") == "TRANSACCION_COMPLETA":
            payment.status = 'confirmed'  # o 'paid', según tu configuración
        elif response.get("estado") == "TRANSACCION_RECHAZADA":
            payment.status = 'rejected'
        elif response.get("estado") == "PENDIENTE":
            payment.status = 'pending'
        else:
            payment.status = 'error'  # Otro estado no esperado

        # Guardar la actualización
        payment.save()

        return response

    except RedirectNeeded as redirect_to:
        return redirect(str(redirect_to))


def payment_success(request, pk):
    if request.method == "POST":
        print('peo')
        if 'submit' in request.POST:
            print('peoo')
            idPago = request.POST.get('pago')
            pago = Payment.objects.filter(payment_id = idPago).first()
            pago.status = 'approved'
            pago.save()
            cliente = Cliente.objects.filter(usuario = request.user.username).first()
            carrito = CarritoCompra.objects.filter(idcliente = cliente, estado = 1).first()
            detalle = DetalleCarrito.objects.filter(idcarrito = carrito)

            Pago.objects.create(
                idPagoAPI = pago,
                rut = cliente.rut
            )

            for productos in detalle:
                producto = Inventario.objects.filter(idproducto = productos.idproducto.idproducto).first()
                producto.stock = producto.stock - productos.cantidad
                producto.save()



            carrito.estado = 0
            carrito.save()

            return redirect('index')
    return render(request, 'success.html', {'payment_id': pk})

def payment_pending(request):
    return render(request, 'pagos/pending.html')

def payment_failure(request):
    return render(request, 'pagos/failure.html')
