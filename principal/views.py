from datetime import date
from textwrap import wrap
from django.utils import timezone
from decimal import Decimal
from django.db.models import Q
import io
import json
from django.utils.timezone import now
import subprocess
import unicodedata
from uuid import UUID
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
import qrcode
import requests
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from payments import get_payment_model, RedirectNeeded
from payments.core import provider_factory
from django.db.transaction import atomic
from urllib.parse import quote
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import logging
from pagos.models import Payment
from django_payments_chile import WebpayProvider
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from principal.forms import RegistroForm
from principal.models import CarritoCompra, Cliente, DetalleCarrito, Inventario, Pago
from .utilities import traducir_html
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
from PIL import Image
import pandas as pd
from .models import Descuento, DetalleVenta, Inventario, Vendedor, Venta
from django.core.mail import send_mail



logger = logging.getLogger(__name__)

def git_commit(commit_message):

  # Agregar todos los cambios

  subprocess.run(["git", "add", "."])



  # Hacer el commit

  subprocess.run(["git", "commit", "-m", commit_message])



  # Hacer push a la rama principal (main)

  subprocess.run(["git", "push", "origin", "main"])


def enviar_correo():
    asunto = 'Correo de prueba desde Django'
    mensaje = 'Hola, este es un correo enviado usando Django.'
    remitente = 'tucorreo@gmail.com'
    destinatarios = ['destinatario@example.com']

    send_mail(asunto, mensaje, remitente, destinatarios)


def traducir_template(request):
    html_original = render_to_string("cuenta.html", {"usuario": request.user})
    html_traducido = traducir_html(html_original, "FR")  # Cambia "FR" por el idioma destino (FR, EN, DE, etc.)
    return HttpResponse(html_traducido)

# Create your views here.
def index(request):
    tasa_conversion = 0
    login_form = AuthenticationForm()
    registro_form = RegistroForm()
    precio = 10000
    
    idioma = request.GET.get('traduccion')
    moneda = 'CLP'
    cliente = Cliente.objects.filter(usuario=request.user.username).first()
    carrito = CarritoCompra.objects.filter(idcliente=cliente).first()
    detalle = DetalleCarrito.objects.filter(idcarrito = carrito)
    total = 0

    producto1 = Inventario.objects.filter(categoria = 'Herramientas Electricas').first()
    producto2 = Inventario.objects.filter(categoria = 'Herramientas y Maquinarias de Construccion').first()
    producto3 = Inventario.objects.filter(categoria = 'Madera').first()
    producto4 = Inventario.objects.filter(categoria = 'Ventanas').first()

    print(f'producto 1: {producto1.idproducto}')

    print(f"cliente: {cliente}")
    print(f"carrito: {carrito}")
    print(f"detalle: {detalle}")

    for i in detalle:
        total+= i.idproducto.precio * i.cantidad
    print(total)

    if request.user.groups.filter(name='vendedores').exists():
        tipo_usuario = 'vendedor'
    elif request.user.groups.filter(name='contadores').exists():
        tipo_usuario = 'contador'
    elif request.user.groups.filter(name='bodegueros').exists():
        tipo_usuario = 'bodeguero'
    else:
        tipo_usuario = 'admin'

    print(f"tipo de usuario: {tipo_usuario}")


    if request.method == "GET":
        if 'traduccion' in request.GET:
            
            idioma = request.GET.get('traduccion')
            print(f"idioma: {idioma}")
            html_original = render_to_string("index.html", {"usuario": request.user, 'producto1':producto1,
        'producto2':producto2,
        'producto3':producto3,
        'producto4':producto4,})
            html_traducido = traducir_html(html_original, idioma)  # Cambia "FR" por el idioma destino (FR, EN, DE, etc.)
            return HttpResponse(html_traducido)

    if request.method == "POST":
        tasa_conversion = 0

        if 'borrar' in request.POST:
            producto = request.POST.get('producto')
            Borrar_producto = DetalleCarrito.objects.filter(idproducto=producto)
            Borrar_producto.delete()
            return redirect('index')

        # FORMULARIO LOGIN
        if 'login_form' in request.POST:
            login_form = AuthenticationForm(request, data=request.POST)
            print(f"form: {login_form}")
            if login_form.is_valid():
                username = login_form.cleaned_data.get('username')
                password = login_form.cleaned_data.get('password')
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('index')
                else:
                    messages.error(request, "Usuario o contraseña inválidos.")
            else:
                print('tonto')
                messages.error(request, "Usuario o contraseña inválidos.")


        # FORMULARIO REGISTRO
        elif 'registro_form' in request.POST:
            registro_form = RegistroForm(request.POST)
            if registro_form.is_valid():
                user = registro_form.save()
                Cliente.objects.create(
                    usuario = request.POST.get('username'),
                    nombre = "",
                    apellido = "",
                    rut = request.POST.get('rut'),
                    correo = request.POST.get('email'),
                    contrasena = request.POST.get('password1'),
                    direccion = "",
                    telefono = "",
                    fecha_registro = date.today()
                )
                login(request, user)
                git_commit("registro usuario")
                return redirect('index')
            else:
                messages.error(request, "Error al registrar el usuario.")

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
    return render(request, 'index.html', {
        'precio': precio * tasa_conversion if tasa_conversion>0 else precio, 
        'login_form': login_form, 
        'registro_form': registro_form, 
        'tipo_usuario': tipo_usuario, 
        'idioma': idioma if idioma != None else 'ES', 
        'moneda':moneda if moneda !=None else 'CLP',
        'producto1':producto1,
        'producto2':producto2,
        'producto3':producto3,
        'producto4':producto4,
    })



def productos(request, categoria):

    # Obtener productos según categoría
    if categoria == 'todos':
        productos = Inventario.objects.all()
    else:
        productos = Inventario.objects.filter(categoria=categoria)
        

    # Total carrito
    carrito = DetalleCarrito.objects.all()
    total = sum(i.idproducto.precio * i.cantidad for i in carrito)

    # Por defecto
    moneda = ""
    tasa_conversion = 1

    # Manejo POST: moneda, borrar, login, registro, etc.
    if request.method == "POST":

        # Cambio de moneda
        moneda_post = request.POST.get("moneda", "").upper()
        monedas_validas = ["USD", "EUR", "CAD", "CLP"]
        if moneda_post in monedas_validas:
            moneda = moneda_post
            url = f"https://v6.exchangerate-api.com/v6/e62c5a2d52f4a1d6b195a3b8/latest/CLP"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    tasa_conversion = data["conversion_rates"].get(moneda, 1)
            except Exception as e:
                print(f"Error al obtener tasa de cambio: {e}")

        # Borrar producto del carrito
        if 'borrar' in request.POST:
            producto_id = request.POST.get('producto')
            DetalleCarrito.objects.filter(idproducto=producto_id).delete()

        # Traducción vía POST (compatibilidad)
        if 'traduccion' in request.POST:
            idioma = request.POST.get('traduccion', 'FR')
            # Se hará más abajo para mantener el contexto completo

        # Manejo login
        if 'login_form' in request.POST:
            login_form = AuthenticationForm(data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, "Usuario o contraseña inválidos.")

        # Manejo registro
        elif 'registro_form' in request.POST:
            registro_form = RegistroForm(request.POST)
            if registro_form.is_valid():
                user = registro_form.save()
                Cliente.objects.create(
                    usuario=request.POST.get('username'),
                    correo=request.POST.get('email'),
                    contrasena=request.POST.get('password1'),
                    nombre="", apellido="", rut="",
                    direccion="", telefono="",
                    fecha_registro=date.today()
                )
                login(request, user)
                git_commit("registro usuario")
                return redirect('index')
            else:
                messages.error(request, "Error al registrar el usuario.")

    # Aplicar tasa de cambio a productos
    productos_actualizados = []
    for p in productos:
        p.precio_convertido = round(p.precio * tasa_conversion, 2)
        productos_actualizados.append(p)

    # Paginación
    paginator = Paginator(productos_actualizados, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Construir contexto completo
    context = {
        "usuario": request.user,
        "productos": productos_actualizados,
        "categoria": categoria,
        "tasa": tasa_conversion,
        "moneda": moneda if moneda else "CLP",
        #"total": total,
        "page_obj": page_obj,
    }

    productos_sin_imagen = []
    for p in productos_actualizados:
        producto_sin_imagen = {
        'idproducto': p.idproducto,
        'nombre': p.nombre,
        'precio': p.precio,
        'stock':p.stock,
        # cualquier otro campo que uses en la plantilla
        'imagen_base64': '',  # vacío para que no envíe la imagen
        }
        productos_sin_imagen.append(producto_sin_imagen)

    # Traducción (GET o POST)
    if request.method == "GET":
        if 'traduccion' in request.GET:
            idioma = request.GET.get('traduccion')
            print(f"idioma: {idioma}")

            paginator = Paginator(productos_sin_imagen, 12)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            # Renderizar sin imagen
            html_original = render_to_string("productos.html", {
                "usuario": request.user,
                'idioma': idioma,
                'page_obj': page_obj,
                'traduciendo': True,  # bandera para el template
            })

            html_traducido, _ = traducir_html(html_original, idioma)  # ← aquí tomas solo el HTML

            # Reinsertar imagen directamente si quieres
            for producto in productos_actualizados:
                print(producto.imagen_base64)
                marcador = '<!-- IMAGEN_PRODUCTO_{{' + str(producto.idproducto) + '}} -->'
                imagen_html = '<img src="data:image/jpeg;base64, {{ ' + producto.imagen_base64 + ' }}" alt="Producto" class="card-img-top">'
                html_traducido = html_traducido.replace(marcador, imagen_html)

            return HttpResponse(html_traducido)
    return render(request, 'productos.html', context)

def unitario(request, productoID):
    producto = Inventario.objects.filter(idproducto = productoID).first()
    producto_sin_imagen = {
    'idproducto': producto.idproducto,
    'nombre': producto.nombre,
    'precio': producto.precio,
    'stock':producto.stock,
    # cualquier otro campo que uses en la plantilla
    'imagen_base64': '',  # vacío para que no envíe la imagen
}
    print(producto)
    if request.method == "GET":
        if 'traduccion' in request.GET:
            idioma = request.GET.get('traduccion')
            print(f"idioma: {idioma}")

            # Renderizar sin imagen
            html_original = render_to_string("unitario.html", {
                "usuario": request.user,
                'idioma': idioma,
                'producto': producto_sin_imagen,
                'traduciendo': True,  # bandera para el template
            })

            html_traducido, _ = traducir_html(html_original, idioma)  # ← aquí tomas solo el HTML

            # Reinsertar imagen directamente si quieres
            imagen_html = f'<img src="data:image/jpeg;base64,{producto.imagen_base64}" alt="Producto" class="card-img-top">'
            html_final = html_traducido.replace('<!-- IMAGEN_AQUI -->', imagen_html)

            return HttpResponse(html_final)
    print(productoID)
    if request.method == "POST":
        if 'borrar' in request.POST:
            producto = request.POST.get('producto')
            Borrar_producto = DetalleCarrito.objects.filter(idproducto=producto)
            Borrar_producto.delete()
            return redirect(f'/unitario/{productoID}')

    
    return render(request, 'unitario.html', {'producto':producto})

@login_required
def cuenta(request):
    correo = request.user.email
    usuario = Cliente.objects.filter(correo = correo).first()
    print(f"usuario: {usuario}")

    if request.user.groups.filter(name='vendedores').exists():
        tipo_usuario = 'vendedor'
    else:
        tipo_usuario = 'contador'

    print(f"tipo de usuario: {tipo_usuario}")


    if request.method == 'POST':
        if 'logout' in request.POST:
            logout(request)
            return redirect('index')
        usuario.nombre = request.POST.get('nombre', usuario.nombre)
        usuario.apellido = request.POST.get('apellido', usuario.apellido)
        usuario.telefono = request.POST.get('telefono', usuario.telefono)
        usuario.direccion = request.POST.get('direccion', usuario.direccion)
        usuario.save()
        #git_commit("actualizacion perfil")
        return redirect('cuenta')
    
    return render(request, 'cuenta.html', {'usuario': usuario, 'tipo_usuario':tipo_usuario})

def carrito(request):
    carrito = DetalleCarrito.objects.all()
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

def webpay_cancel(request):
    """Vista para manejar cancelaciones desde Webpay."""
    # Puedes leer los parámetros como TBK_TOKEN, TBK_ORDEN_COMPRA, etc.
    tbk_token = request.GET.get('TBK_TOKEN')
    orden = request.GET.get('TBK_ORDEN_COMPRA')
    
    # Aquí podrías registrar el intento fallido en logs, base de datos, etc.

    return render(request, 'pagos/cancel.html', {
        'orden': orden,
        'tbk_token': tbk_token,
    })


def resumen(request):
    session_key = request.session.session_key
    cliente = Cliente.objects.filter(usuario = request.user.username).first()
    if request.user.is_authenticated:
        carrito = CarritoCompra.objects.filter(idcliente = cliente, estado=1).first()
    else:
        carrito = CarritoCompra.objects.filter(session_key = session_key, estado=1).first()
    detalle = DetalleCarrito.objects.filter(idcarrito = carrito)
    total = 0
    subtotal = 0
    totalPago = 0

    print(f'carrito: {detalle}')

    if not detalle.exists():
        return redirect('index')

    for i in detalle:
        total+= i.idproducto.precio * i.cantidad
        totalPago = total
    print(total)

    if request.method == 'POST':
        if 'borrar' in request.POST:
            print("peo")
            producto = request.POST.get('producto_borrado')
            Borrar_producto = DetalleCarrito.objects.filter(idproducto=producto)
            Borrar_producto.delete()
            usuario = Cliente.objects.filter(usuario=request.user.username).first()
            carro = CarritoCompra.objects.filter(idcliente=usuario, estado = 1).first()
            validar_carrito = DetalleCarrito.objects.filter(idcarrito=carro).first()
            print(f"carrito: {validar_carrito}")
            if validar_carrito != None:
                return redirect('resumen')
            else:
                return redirect('index')

        if 'aplicarDescuento' in request.POST: 
            codigo = request.POST.get('codigo')
            descuentos = Descuento.objects.filter(codigo=codigo).first() 
            if descuentos != None:
                subtotal = total * (descuentos.descuento/100)
                totalPago = total - subtotal
    return render(request, 'resumen.html', {
        'subtotal':subtotal,
        'total':total,
        'totalPago':int(totalPago)
        })

def pago(request, total):

    carrito = DetalleCarrito.objects.all()
    #total = 0
    cliente = Cliente.objects.filter(usuario = request.user.username).first()

    if not carrito.exists():
        return redirect('index')

    #for i in carrito:
    #    total+= i.idproducto.precio * i.cantidad
    print(total)
    payment_model = get_payment_model()  # Obtienes el modelo de pago de django-payments

    if request.method == 'POST':
        monto = request.POST.get('valor')
        metodoPago = request.POST.get('metodoPago')
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        email = request.POST.get('correo')
        tipoDoc = request.POST.get('tipoDoc')
        codigo = request.POST.get('prefijo')
        numero = request.POST.get('telefono')
        direccion = request.POST.get('direccion_envio')
        retiro = request.POST.get('sucursal')
        print(f'tipoDoc: {tipoDoc}')
        if metodoPago == 'webpay':
            try:
                # Crear un objeto de pago
                payment = payment_model.objects.create(
                    variant="webpay",  # Debe coincidir con el nombre configurado en PAYMENT_VARIANTS
                    description="Pago por Orden #123",
                    total=int(monto),  # Monto en centavos (10000 = 100 pesos)
                    currency="CLP",
                    billing_first_name=nombre,
                    billing_last_name=apellido,
                    billing_email=email,
                    billing_phone=codigo + numero,
                    tipo_documento=tipoDoc,
                    billing_address_1=direccion or "",
                    billing_address_2= retiro or None

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
        elif metodoPago == 'paypal':
            try:
                # Crear un objeto de pago
                payment = payment_model.objects.create(
                    variant="paypal",  # Debe coincidir con el nombre configurado en PAYMENT_VARIANTS
                    description="Pago por Orden #123",
                    total=Decimal(monto),  # Monto en centavos (10000 = 100 pesos)
                    currency="USD",
                    billing_first_name="Juan",
                    billing_last_name="Pérez",
                    billing_email=email,
                    captured_amount=Decimal("0.00"),
                    delivery = Decimal("0.00"),
                    tax = Decimal("0.00"),
                )


                print("TIPO total:", type(payment.total), "VALOR:", payment.total)
                print("TIPO captured_amount:", type(payment.captured_amount), "VALOR:", payment.captured_amount)

                # Parche temporal si es string
                if isinstance(payment.captured_amount, str):
                    payment.captured_amount = Decimal(payment.captured_amount)
                # Obtener el formulario que hace POST automáticamente a Webpay
                form = payment.get_form()
                

                # Mostrar el formulario para que el navegador lo envíe automáticamente a Webpay
                return render(request, 'redirigir_webpay.html', {'form': form})

            except RedirectNeeded as redirect_to:
                return redirect(str(redirect_to))
            except Exception as e:
                logger.error(f"Error al crear pago: {str(e)}")
                return HttpResponse(f"Hubo un error: {str(e)}")
        elif metodoPago == 'transferencia':
            return redirect('datosTransferencias')
    
    
    return render(request, 'pago.html', {
        'carrito': carrito, 
        'total':int(total),
        'cliente':cliente
        })


@login_required
def admin(request):
    if request.method == 'POST':
        if 'logout' in request.POST:
            logout(request)
            return redirect('index')
    return render(request, 'admin.html')

@login_required
def contador(request):
    return render(request, 'contador.html')

def nosotros(request):
    if request.method == "GET":
        if 'traduccion' in request.GET:
            
            idioma = request.GET.get('traduccion')
            print(f"idioma: {idioma}")
            html_original = render_to_string("nosotros.html", {"usuario": request.user, 'idioma':idioma})
            html_traducido = traducir_html(html_original, idioma)  # Cambia "FR" por el idioma destino (FR, EN, DE, etc.)
            return HttpResponse(html_traducido)
    return render(request, 'nosotros.html')

def TerminosyCondiciones(request):
    return render(request, 'TerminosyCondiciones.html')

def Cambios(request):
    return render(request, 'Cambios.html')

def base(request):
    carrito = DetalleCarrito.objects.all()
    print(carrito)
    return render(request, 'base.html', {'carrito':carrito})

def contacto(request):
    return render(request, 'contacto.html')

@login_required
def gestionCatalogo(request):
    productos = Inventario.objects.all()

    if request.method == "POST":
        # ✅ SUBIDA DE EXCEL
        if request.FILES.get('archivo_excel'):
            archivo_excel = request.FILES['archivo_excel']
            errores = []
            productos_creados = 0
            productos_actualizados = 0

            try:
                df = pd.read_excel(archivo_excel)

                for index, row in df.iterrows():
                    fila = index + 2  # Fila real en el Excel (considerando encabezado)

                    nombre = str(row.get('nombre')).strip() if pd.notna(row.get('nombre')) else ''
                    descripcion = str(row.get('descripcion')).strip() if pd.notna(row.get('descripcion')) else ''
                    stock = int(float(row.get('stock'))) if pd.notna(row.get('stock')) else 0
                    try:
                        precio = int(float(row.get('precio'))) if pd.notna(row.get('precio')) else 0
                    except:
                        precio = 0
                    categoria_nombre = str(row.get('categoria')).strip() if pd.notna(row.get('categoria')) else ''
                    marca = str(row.get('marca')).strip() if pd.notna(row.get('marca')) else ''
                    imagen_base64 = str(row.get('imagen_base64')).strip() if pd.notna(row.get('imagen_base64')) else ''

                    # Validación mínima
                    if not nombre:
                        errores.append(f"Fila {fila}: El campo 'nombre' está vacío.")
                        continue

                    try:
                        producto, creado = Inventario.objects.get_or_create(
                            nombre=nombre,
                            defaults={
                                'descripcion': descripcion,
                                'stock': stock,
                                'precio': precio,
                                'categoria': categoria_nombre,
                                'alerta': False,
                                'fecha_actualizacion': date.today(),
                                'imagen_base64': imagen_base64,
                                'precio_convertido': 0,
                                'marca': marca,
                            }
                        )

                        if creado:
                            productos_creados += 1
                        else:
                            producto.descripcion = descripcion
                            producto.stock = stock
                            producto.precio = precio
                            producto.categoria = categoria_nombre
                            producto.fecha_actualizacion = date.today()
                            producto.marca = marca
                            producto.imagen_base64 = imagen_base64
                            producto.save()
                            productos_actualizados += 1

                    except Exception as e:
                        errores.append(f"Fila {fila}: Error al crear/actualizar producto: {str(e)}")
                        continue

                if errores:
                    for err in errores:
                        messages.warning(request, err)

                messages.success(request, f"Excel procesado: {productos_creados} producto(s) creado(s), {productos_actualizados} actualizado(s).")
                #git_commit("Subida de productos por Excel")

            except Exception as e:
                messages.error(request, f"Error al leer el archivo: {str(e)}")

            return redirect('gestionCatalogo')
        # ✅ CREAR PRODUCTO
        if 'crear' in request.POST:
            nombre = request.POST.get('nombre') 
            descripcion = request.POST.get('descripcion')
            precio = request.POST.get('precio')
            stock = request.POST.get('stock')
            imagen = request.POST.get('imageBase64')
            marca = request.POST.get('marca')
            categoria = request.POST.get('categoria')

            Inventario.objects.create(
                nombre=nombre or "",
                descripcion=descripcion or "",
                marca=marca or "",
                categoria=categoria or "",
                stock=int(stock) if stock else 0,
                alerta=False,
                fecha_actualizacion=date.today(),
                imagen_base64=imagen or "",
                precio=int(precio) if precio else 0,
                precio_convertido=0
            )
            #git_commit("creación producto")
            return redirect('gestionCatalogo')

        # ✅ EDITAR PRODUCTO
        if 'editar' in request.POST:
            editarCodigo = request.POST.get('editarCodigo')
            imagenActual = request.POST.get('imagenActual')
            producto_editado = Inventario.objects.filter(idproducto=editarCodigo).first()

            if producto_editado:
                producto_editado.nombre = request.POST.get('editarNombre') or ""
                producto_editado.descripcion = request.POST.get('editarDescripcion') or ""
                producto_editado.marca = request.POST.get('editarMarca') or ""
                producto_editado.categoria = request.POST.get('editarCategoria') or producto_editado.categoria
                producto_editado.stock = int(request.POST.get('editarStock') or 0)
                producto_editado.alerta = False
                producto_editado.fecha_actualizacion = date.today()
                producto_editado.precio = int(request.POST.get('editarPrecio') or 0)
                producto_editado.imagen_base64 = request.POST.get('imageBase64Editada') or imagenActual
                producto_editado.precio_convertido = 0

                producto_editado.save()
                #git_commit("edición producto")
            return redirect('gestionCatalogo')

    return render(request, 'gestionCatalogo.html', {'productos': productos})


@login_required
def gestionDescuento(request):
    descuentos = Descuento.objects.all()
    for d in descuentos:
        if d.fechaTermino < timezone.now():
            d.estado = 0
            d.save()
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        codigo = request.POST.get('codigo')
        descuento = request.POST.get('descuento')
        inicio = request.POST.get('inicio')
        termino = request.POST.get('termino')

        validacion = Descuento.objects.filter(codigo= codigo).first()
        if validacion != None:
            return redirect('gestionDescuento')

        Descuento.objects.create(
            nombreDescuento = nombre,
            codigo=codigo,
            descuento = descuento,
            fechaInicio=inicio,
            fechaTermino=termino,
            estado=1
        )
        return redirect('gestionDescuento')
    return render(request, 'gestionDescuento.html', {
        'descuentos':descuentos
    })

def cerrar_sesion(request):
    logout(request)
    return redirect('index')

@login_required
def gestionInventario(request):
    return render(request, 'gestionInventario.html')

@login_required
def vendedor(request):
    return render(request, 'vendedor.html')

@login_required
def gestionPedidos(request):
    return render(request, 'gestionPedidos.html')

@login_required
def gestionPagos(request):
    pagos = Pago.objects.all()
    for pago in pagos:
        if isinstance(pago.idPagoAPI.extra_data, str):
            try:
                pago.idPagoAPI.extra_data = json.loads(pago.idPagoAPI.extra_data)
            except json.JSONDecodeError:
                pago.idPagoAPI.extra_data = {}
        if pago.idPagoAPI.status == 'approved':
            pago.idPagoAPI.status = 'Aprobado'
            pago.save()
    return render(request, 'gestionPagos.html', {'pagos':pagos})

@login_required
def transferencias(request):
    return render(request, 'transferencias.html')

@login_required
def reportesFinancieros(request):
    return render(request, 'reportesFinancieros.html')

@login_required
def gestionReportesAdmin(request):
    productos = Inventario.objects.all()

    productosCriticos = []
    for p in productos:
        if p.stock <= 5:
            productosCriticos.append(p)

    if request.method == 'POST':
        if 'alerta' in request.POST:
            idProducto = request.POST.get('idProducto')
            print(f'id: {idProducto}')
            productoCritico = Inventario.objects.filter(idproducto=idProducto).first()
            print(f'producto: {productoCritico}')
            productoCritico.alerta = 1
            productoCritico.save()
            return redirect('gestionReportesAdmin')
    return render(request, 'gestionReportesAdmin.html', {
        'productos':productos,
        'productosCriticos':productosCriticos

    })


@login_required
def gestionVenta(request):
    detalle = None
    if request.user.is_authenticated:
        usuario = Vendedor.objects.filter(usuario=request.user.username).first()

        # Carga la venta activa (si existe)
        venta = Venta.objects.filter(idvendedor=usuario, estado=1).first()

        if venta:
            detalle = DetalleVenta.objects.filter(idventa=venta)

        if request.method == 'POST':
            print('hola mundo')

            if request.POST.get('submit') == "addtocart":
                venta, creado = Venta.objects.get_or_create(
                    idvendedor=usuario,
                    estado=1,
                    defaults={'fechacreacion': date.today()}
                )

                id_producto = request.POST.get('id_producto')
                cantidad = int(request.POST.get('product-quantity'))

                producto = Inventario.objects.filter(idproducto=id_producto).first()
                detalle_item = DetalleVenta.objects.filter(idventa=venta, idproducto=id_producto).first()

                if producto:
                    if detalle_item:
                        detalle_item.cantidad += cantidad
                        detalle_item.save()
                    else:
                        DetalleVenta.objects.create(
                            idventa=venta,
                            idproducto=producto,
                            cantidad=cantidad,
                        )
                else:
                    return redirect('gestionVenta')

                #git_commit("creacion carrito")

                return redirect('gestionVenta')
            
            if request.POST.get('submit') == "borrar":
                idProducto = request.POST.get('idProducto')

                producto = Inventario.objects.filter(idproducto=idProducto).first()
                detalle_item = DetalleVenta.objects.filter(idventa=venta, idproducto=idProducto).first()

                detalle_item.delete()

                #git_commit("creacion carrito")

                return redirect('gestionVenta')
    total_general = sum(item.total() for item in detalle) if detalle else 0
    return render(request, 'gestionVenta.html', {
        'detalle': detalle,
        'total_general':total_general
    })

@login_required
def bodeguero(request):
    return render(request, 'bodeguero.html')

@login_required
def entregaPedidos(request):
    return render(request, 'entregaPedidos.html')

@login_required
def preparacionDespacho(request):
    return render(request, 'preparacionDespacho.html')

@login_required
def verOrdenes(request):
    return render(request, 'verOrdenes.html')

@login_required
def entregasContador(request):
    return render(request, 'entregasContador.html')



def agregarCarrito(request):
    print(request.user)
    if request.user.is_authenticated:
        if request.method == 'POST':
            usuario = Cliente.objects.filter(usuario=request.user.username).first()
            if request.POST.get('submit') == "addtocart":
                carrito, creado = CarritoCompra.objects.get_or_create(
                    idcliente=usuario,
                    estado= 1,  # Asegúrate que este campo existe
                    defaults={'fechacreacion': date.today()}
                )

                id_producto = request.POST.get('id_producto')
                cantidad = int(request.POST.get('product-quantity'))
                template = request.POST.get('template')

                detalle = DetalleCarrito.objects.filter(idcarrito=carrito.idcarrito, idproducto=id_producto).first()
                producto = Inventario.objects.filter(idproducto=id_producto).first()

                if detalle:
                    detalle.cantidad += cantidad
                    detalle.save()
                else:
                    DetalleCarrito.objects.create(
                        idcarrito=carrito,
                        idproducto=producto,
                        cantidad=cantidad,
                    )

                #git_commit("creacion carrito")

                categoria = request.POST.get('categoria')
                busqueda = request.POST.get('busqueda')

                if template == 'unitario':
                    return redirect(f'{template}/{id_producto}')
                else:
                    if categoria:
                        return redirect(f'/productos/{quote(categoria)}')
                    elif busqueda:
                        return redirect(f'/buscar?busqueda={quote(busqueda)}')
    
    else:
        print('holamundo sin POST')
        if request.method == 'POST':
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            if request.POST.get('submit') == "addtocart":
                carrito, _ = CarritoCompra.objects.get_or_create(
                    idcliente=None,
                    session_key=session_key,
                    estado=1,
                    defaults={'fechacreacion': date.today()}
                )

                id_producto = request.POST.get('id_producto')
                cantidad_solicitada = int(request.POST.get('product-quantity', 1))
                template = request.POST.get('template')

                producto = Inventario.objects.filter(idproducto=id_producto).first()
                if not producto:
                    messages.error(request, "Producto no encontrado.")
                    return redirect('pagina_de_error')

                detalle = DetalleCarrito.objects.filter(idcarrito=carrito.idcarrito, idproducto=id_producto).first()

                cantidad_en_carrito = detalle.cantidad if detalle else 0
                stock_disponible = producto.stock

                categoria = request.POST.get('categoria')
                busqueda = request.POST.get('busqueda')

                # ✅ Validación principal
                if cantidad_en_carrito + cantidad_solicitada > stock_disponible:
                    messages.error(request, f"No puedes agregar más de {stock_disponible} unidades en total.")
                    if template == 'unitario':
                        return redirect(f'{template}/{id_producto}')  # Cambia esto por tu ruta real
                    else:
                        if categoria:
                            return redirect(f'/productos/{quote(categoria)}')
                        elif busqueda:
                            return redirect(f'/buscar?busqueda={quote(busqueda)}')

                if detalle:
                    detalle.cantidad += cantidad_solicitada
                    detalle.save()
                else:
                    DetalleCarrito.objects.create(
                        idcarrito=carrito,
                        idproducto=producto,
                        cantidad=cantidad_solicitada,
                    )

                #git_commit("creación carrito")

                # Redirección limpia
                

                if template == 'unitario':
                    return redirect(f'{template}/{id_producto}')
                elif categoria:
                    return redirect(f'/productos/{quote(categoria)}')
                elif busqueda:
                    return redirect(f'/buscar?busqueda={quote(busqueda)}')
                
    return render(request, 'productos.html')


def actualizarCarrito(request):
    
    if request.method == 'POST':
        id_producto = request.POST.get('producto')
        categoria = request.POST.get('categoria')
        operacion = request.POST.get('operacion')
        cliente = Cliente.objects.filter(usuario=request.user.username).first()
        if cliente:
            carrito = CarritoCompra.objects.filter(idcliente=cliente.idcliente).first()
        else:
            session_key = request.session.session_key
            carrito = CarritoCompra.objects.filter(session_key=session_key).first()
        detalle = DetalleCarrito.objects.filter(idcarrito=carrito, idproducto=id_producto).first()
        producto = Inventario.objects.filter(idproducto = id_producto).first()
        print(f"carrito: {carrito}")
        print(f"detalle: {detalle}")
        print(f"operacion: {operacion}")
        if detalle:
            if operacion == "menos":
                if detalle.cantidad > 1:
                    detalle.cantidad -= 1
                else:
                    detalle.delete()
                    messages.info(request, 'Producto eliminado del carrito.')
                    return redirect('resumen')
            elif operacion == "mas":
                detalle.cantidad += 1
                if detalle.cantidad > producto.stock:
                    messages.warning(request, 'Usted ha alcanzado el límite de productos disponibles.')
                    detalle.cantidad -= 1
                    return redirect('resumen')
            detalle.save()

            return redirect('resumen') 
    return redirect('resumen')

def borrar(request, productoID, html):
    if html == 'gestionCatalogo':
        
        producto = Inventario.objects.filter(idproducto = int(productoID)).first()
        producto.delete()
    elif html == 'gestionDescuento':
        descuento = Descuento.objects.filter(codigo=productoID).first()
        descuento.delete()
    return redirect(html)



def generar_comprobante_pdf(request, pago_id: UUID):
    from .models import Pago  # importa tu modelo real
    pago = Pago.objects.get(idPagoAPI=pago_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=comprobante_{pago_id}.pdf'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, height - 50, "Comprobante de Pago")

    # Fecha
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 80, f"Fecha: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

    # Datos del pago
    p.setFont("Helvetica", 12)
    y = height - 120

    if isinstance(pago.idPagoAPI.extra_data, str):
        try:
            pago.idPagoAPI.extra_data = json.loads(pago.idPagoAPI.extra_data)
        except json.JSONDecodeError:
            pago.idPagoAPI.extra_data = {}
    if pago.idPagoAPI.status == 'approved':
        pago.idPagoAPI.status = 'Aprobado'
        pago.save()

    datos = {
        "ID Pago": pago.idPagoAPI.id,
        "Estado": pago.idPagoAPI.status,
        "Monto": pago.idPagoAPI.total,
        "Tipo de pago": pago.idPagoAPI.extra_data.get('commit_response', {}).get('payment_type_code_str', 'N/A'),
        "Código autorización": pago.idPagoAPI.extra_data.get('commit_response', {}).get('authorization_code', 'N/A'),
        "Fecha transacción": pago.idPagoAPI.extra_data.get('commit_response', {}).get('transaction_date', 'N/A'),
    }

    for key, value in datos.items():
        p.drawString(50, y, f"{key}: {value}")
        y -= 20

    p.showPage()
    p.save()

    return response


def generar_comprobante(request):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Obtener vendedor
    vendedor = Vendedor.objects.filter(usuario=request.user.username).first()
    venta = Venta.objects.filter(idvendedor=vendedor, estado=1).first()  # Venta activa

    if not venta:
        return HttpResponse("No hay venta activa", status=400)

    detalles = DetalleVenta.objects.filter(idventa=venta)

    empresa = "FERREMAS"
    fecha = now().strftime('%d/%m/%Y %H:%M')
    y = height - 100
    total_general = 0

    # Título y fecha
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, height - 40, f"COMPROBANTE DE VENTA - {empresa}")
    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(width - 40, height - 60, f"Fecha: {fecha}")

    # Encabezado tabla
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Producto")
    pdf.drawString(200, y, "Cantidad")
    pdf.drawString(280, y, "P. Unitario")
    pdf.drawString(380, y, "Subtotal")
    y -= 20

    pdf.setFont("Helvetica", 10)
    for item in detalles:
        producto = item.idproducto.nombre
        cantidad = item.cantidad
        precio = item.idproducto.precio
        subtotal = cantidad * precio
        total_general += subtotal

        # Envolver nombre en líneas de 30 caracteres
        lineas = wrap(producto, 30)

        # Escribir cada línea del nombre
        for i, linea in enumerate(lineas):
            pdf.drawString(40, y - (i * 12), linea)

        # Escribir los demás datos en la primera línea
        pdf.drawString(200, y, str(cantidad))
        pdf.drawString(280, y, f"${precio:,}")
        pdf.drawString(380, y, f"${subtotal:,}")

        # Ajustar el cursor vertical según las líneas del nombre
        y -= max(20, 12 * len(lineas))

    # Total final
    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, f"Total a Pagar: ${total_general:,}")

    # QR con resumen
    qr_data = f"{empresa} - Total: ${total_general:,}, Fecha: {fecha}"
    qr_img = qrcode.make(qr_data)
    qr_io = io.BytesIO()
    qr_img.save(qr_io, format="PNG")
    qr_io.seek(0)
    pdf.drawInlineImage(Image.open(qr_io), width - 140, y - 100, 100, 100)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    for item in detalles:
        item.delete()
    venta.estado = 0
    venta.save()

    return FileResponse(buffer, as_attachment=True, filename='comprobante_ferremas.pdf')
    return redirect('gestionVenta')


def subir_excel(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        archivo = request.FILES['archivo_excel']
        df = pd.read_excel(archivo)
        print('peo')

        for _, row in df.iterrows():
            idproducto = row.get('idproducto')

            if not idproducto:
                continue  # Salta si no hay ID de producto

            producto, creado = Inventario.objects.get_or_create(idproducto=idproducto)

            # Actualiza los campos (tanto si es nuevo como existente)
            producto.nombre = row.get('nombre', producto.nombre)
            producto.descripcion = row.get('descripcion', producto.descripcion)
            producto.precio = row.get('precio', producto.precio)
            producto.stock = row.get('stock', producto.stock)
            producto.marca = row.get('marca', producto.marca)
            producto.categoria = row.get('categoria', producto.categoria)

            producto.save()

        return redirect('gestionCatalogo')
    return render(request, 'gestionCatalogo.html')

def normalizar_texto(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()

def buscar(request):
    moneda = ""
    tasa_conversion = 1
    busqueda = request.GET.get("busqueda", "")

    # Normaliza y divide en palabras
    busqueda_normalizada = normalizar_texto(busqueda)
    palabras = busqueda_normalizada.split()

    # Construir filtro dinámico
    filtro = Q()
    for palabra in palabras:
        filtro |= Q(nombre__icontains=palabra)
        filtro |= Q(categoria__icontains=palabra)
        # Agrega más campos si lo deseas, por ejemplo:
        # filtro |= Q(descripcion__icontains=palabra)

    productos = Inventario.objects.filter(filtro)

    if request.method == "POST":

        if 'borrar' in request.POST:
            producto = request.POST.get('producto')
            Borrar_producto = DetalleCarrito.objects.filter(idproducto=producto)
            Borrar_producto.delete()
        # Traducción por POST (por compatibilidad)
        if 'traduccion' in request.POST:
            idioma = request.POST.get('traduccion', 'FR')
            html_original = render_to_string("productos.html", {"productos": productos})
            html_traducido = traducir_html(html_original, idioma)
            return HttpResponse(html_traducido)
        
        # LOGIN
        if 'login_form' in request.POST:
            login_form = AuthenticationForm(data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, "Usuario o contraseña inválidos.")

        # REGISTRO
        elif 'registro_form' in request.POST:
            registro_form = RegistroForm(request.POST)
            if registro_form.is_valid():
                user = registro_form.save()
                Cliente.objects.create(
                    usuario=request.POST.get('username'),
                    correo=request.POST.get('email'),
                    contrasena=request.POST.get('password1'),
                    nombre="", apellido="", rut="",
                    direccion="", telefono="",
                    fecha_registro=date.today()
                )
                login(request, user)
                #git_commit("registro usuario")
                return redirect('index')
            else:
                messages.error(request, "Error al registrar el usuario.")

        # CAMBIO DE MONEDA
        moneda = request.POST.get("moneda", "USD").upper()
        moneda_local = "CLP"
        monedas_validas = ["USD", "EUR", "CAD", "CLP"]
        if moneda in monedas_validas:
            url = f"https://v6.exchangerate-api.com/v6/e62c5a2d52f4a1d6b195a3b8/latest/{moneda_local}"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    tasa_conversion = data["conversion_rates"].get(moneda, 1)
            except Exception as e:
                print(f"Error al obtener tasa de cambio: {e}")


    productos_actualizados = []
    for p in productos:
        p.precio_convertido = p.precio * tasa_conversion
        productos_actualizados.append(p)

    paginator = Paginator(productos_actualizados, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'productos.html', {
        'page_obj': page_obj,
        'tasa': tasa_conversion,
        'moneda': moneda if moneda != "" else "CLP",
        })


def datosTransferencias(request):
    return render(request, 'datosTransferencias.html')
