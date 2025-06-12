from datetime import datetime, timedelta
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from payments import get_payment_model, RedirectNeeded
from payments.core import provider_factory
from django.db.transaction import atomic
from django.core.mail import send_mail
import logging
from pagos.models import Payment
from django_payments_chile import WebpayProvider
from django.views.decorators.csrf import csrf_exempt

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics.barcode import code128
from reportlab.lib.units import mm

from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives


from principal.models import Bodeguero, CarritoCompra, Cliente, DetalleCarrito, Inventario, Notificacion, Pago, Pedido, Sucursal

#para produccion
host = 'https://ferremas-svwd.onrender.com'

#para desarrollo
#host = 'http://127.0.0.1:8000'

logger = logging.getLogger(__name__)

def generar_documento_pdf(pago, cliente, detalle_productos, tipo_documento):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40
    # LOGO - Bloque verde con "f"
    c.drawImage('static/img/logo3.png', x=50, y=660, width=300, height=100)
    y -= 90
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(120, y - 20, "Falabella Retail S.A.")
    c.setFont("Helvetica", 9)
    c.drawString(120, y - 35, "RUT: 77.261.280-K")
    c.drawString(120, y - 48, "Casa Matriz: Manuel Rodríguez N° 730, Santiago")
    c.drawString(120, y - 61, "Actividad Económica: 521300")
    y -= 90
    # Título boleta
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, f"BOLETA ELECTRONICA N° {pago.id or '000000000'}")
    y -= 15
    # Datos comercio
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "LOCAL : 2000 - INTERNET")
    y -= 12
    c.drawString(50, y, "DIRECCION : Catedral 1401, Piso 14")
    y -= 12
    c.drawString(50, y, "COMUNA : SANTIAGO")
    y -= 12
    c.drawString(50, y, "Terminal : 3550 Secuencia: 43406")
    y -= 12
    c.drawString(50, y, f"Fecha : {datetime.now().strftime('%d-%m-%Y')} Hora: {datetime.now().strftime('%H:%M')}")
    y -= 12
    c.drawString(50, y, "Vendedor : 217905")
    y -= 12
    c.drawString(50, y, ". VENDEDOR ECOMMERCE")
    y -= 20
    # Detalle productos
    total = 0
    c.line(50, y, width - 50, y)
    y -= 12
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y, "CODIGO PROD DESCRIPCION MONTO")
    y -= 10
    c.setFont("Helvetica", 9)
    for item in detalle_productos:
        nombre = item.idproducto.nombre[:20]
        cantidad = item.cantidad
        precio = item.idproducto.precio
        total_item = precio * cantidad
        total += total_item
        c.drawString(50, y, f"6941812758663 {nombre:<20} ${total_item:,.0f}")
        y -= 12
    y -= 10
    neto = round(total / 1.19)
    iva = total - neto
    c.drawString(50, y, f"SUBTOTAL ${total:,.0f}")
    y -= 12
    c.drawString(50, y, f"NETO ${neto:,.0f}")
    y -= 12
    c.drawString(50, y, f"IVA 19% ${iva:,.0f}")
    y -= 12
    c.drawString(50, y, f"TOTAL ${total:,.0f}")
    y -= 12
    c.drawString(50, y, f"REC TER ECOMMPAY ${total:,.0f}")
    y -= 20
    c.drawString(50, y, f"T {datetime.now().strftime('%d/%m/%y')} 1 VENTA ${total:,.0f} T T")
    y -= 20
    # Código despacho
    c.drawString(50, y, "ORDEN DE DESPACHO : 2831619601/00000000")
    y -= 30
    # Código 2D (simulado con barcode Code128)
    barcode_value = f"{datetime.now().strftime('%d%m%y')}000000{pago.id or '000000'}"
    barcode = code128.Code128(barcode_value, barHeight=25*mm, barWidth=0.5)
    barcode.drawOn(c, 50, y - 25)
    y -= 40
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, "TIMBRE ELECTRONICO SII")
    y -= 10
    c.drawCentredString(width / 2, y, "Res. 140 año 2010. Verifique documento en")
    y -= 10
    c.drawCentredString(width / 2, y, "www.sii.cl")
    y -= 10
    c.drawCentredString(width / 2, y, "Visualice este documento en")
    y -= 10
    c.drawCentredString(width / 2, y, "www.falabella.com")
    y -= 30
    # Código de barras inferior
    code = code128.Code128(barcode_value, barHeight=10*mm, barWidth=0.5)
    code.drawOn(c, 50, y - 10)
    c.drawCentredString(width / 2, y - 15, barcode_value)
    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


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
        if 'submit' in request.POST:
            idPago = request.POST.get('pago')
            pago = Payment.objects.filter(id = idPago).first()
            pago.status = 'Aprobado'
            pago.save()

            cliente = Cliente.objects.filter(usuario = request.user.username).first()
            session_key = request.session.session_key
            if cliente:
                carrito = CarritoCompra.objects.filter(idcliente = cliente, estado = 1).first()
            else:
                carrito = CarritoCompra.objects.filter(session_key = session_key, estado = 1).first()
            detalle = DetalleCarrito.objects.filter(idcarrito = carrito)

            Pago.objects.create(
                idPagoAPI = pago,
                idcliente = cliente or Cliente.objects.filter(idcliente=1).first()
            )

            for productos in detalle:
                producto = Inventario.objects.filter(idproducto = productos.idproducto.idproducto).first()
                producto.stock = producto.stock - productos.cantidad
                producto.save()



            carrito.estado = 0
            carrito.save()

            productos = []
            for producto in detalle:
                detalleProducto = {"nombre": producto.idproducto.nombre, "cantidad": producto.cantidad}
                productos.append(detalleProducto)

            pedido = Pedido.objects.create(
                productos = productos,
                fecha_pedido = datetime.today(),
                estado = 'pendiente',
                tipo_entrega = 'despacho' if pago.billing_address_1 else 'presencial',
                direccion_entrega = pago.billing_address_1 if pago.billing_address_1 else pago.billing_address_2,
                fecha_estimada = datetime.now() + timedelta(weeks=1),
                idPagoAPI = pago,
                idcliente = cliente if cliente else Cliente.objects.filter(idcliente=1).first(),
                notificado = 0
            )
            sucursal = Sucursal.objects.filter(nombre = pago.billing_address_2).first()
            bodegueros = Bodeguero.objects.filter(zona=sucursal)
            correos = []
            for bodeguero in bodegueros:
                correos.append(bodeguero.correo)
            asunto = f'Pedido nro {pedido.idpedido}'
            mensaje = f'Hola, el pedido nro {pedido.idpedido} está confirmado y listo para preparación.'
            remitente = 'ferremas69@gmail.com'
            destinatarios = [correo for correo in correos]

            notificacion = Notificacion.objects.create(
                mensaje=mensaje,
                fecha_envio = datetime.today(),
                leido= 0,
                idvendedor = pedido.idvendedor
            )

            subject = f'Pedido nro {pedido.idpedido}'
            from_email = 'ferremas69@gmail.com'
            to = [correo for correo in correos]

            text_content = f'Hola, el pedido nro {pedido.idpedido} está confirmado y listo para preparación.'
            html_content = f'''
            <p>Hola, ha llegado un nuevo pedido.</p>
            <p>Puedes prepararlo aquí: <a href="{host}/entregaPedidos/1/{notificacion.idnotificacion}">Preparar pedido</a></p>
            '''

            msg = EmailMultiAlternatives(subject, text_content, from_email, to)
            msg.attach_alternative(html_content, "text/html")
            msg.send()


            tipo_documento = pago.tipo_documento  # Asume que message contiene "boleta" o "factura"
            pdf = generar_documento_pdf(pago, cliente or Cliente.objects.filter(idcliente=1).first(), detalle, tipo_documento)

            detalle.delete()

            # Enviar correo con PDF adjunto
            asunto = 'Tu Compra en FERREMAS'
            mensaje = 'Hola, su pago ha sido aprobado.'
            if hasattr(pago, 'billing_address_1') and pago.billing_address_1:
                mensaje += f' El producto será enviado a {pago.billing_address_1}.'
            elif hasattr(pago, 'billing_address_2') and pago.billing_address_2:
                mensaje += f' El producto se podrá retirar en {pago.billing_address_2}.'

            remitente = 'ferremas69@gmail.com'
            destinatarios = [pago.billing_email]

            email = EmailMessage(asunto, mensaje, remitente, destinatarios)
            email.attach(f"{tipo_documento}_{pago.id}.pdf", pdf, "application/pdf")
            email.send()

            return redirect('index')
    return render(request, 'success.html', {'payment_id': pk})


def payment_pending(request):
    return render(request, 'pagos/pending.html')

def payment_failure(request, pk):
    if request.method == "POST":
        if 'submit' in request.POST:
            idPago = request.POST.get('pago')
            pago = Payment.objects.filter(id = idPago).first()
            pago.status = 'Rechazado'
            pago.save()

            cliente = Cliente.objects.filter(usuario = request.user.username).first()
            session_key = request.session.session_key

            Pago.objects.create(
                idPagoAPI = pago,
                idcliente = cliente or Cliente.objects.filter(idcliente=1).first()
            )
            return redirect('pago', total=int(pago.total))
    return render(request, 'failure.html', {'payment_id':pk})
