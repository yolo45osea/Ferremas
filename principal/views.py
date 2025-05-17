from datetime import date
import io
import json
import subprocess
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
from .models import Inventario


logger = logging.getLogger(__name__)

def git_commit(commit_message):

  # Agregar todos los cambios

  subprocess.run(["git", "add", "."])



  # Hacer el commit

  subprocess.run(["git", "commit", "-m", commit_message])



  # Hacer push a la rama principal (main)

  subprocess.run(["git", "push", "origin", "main"])


def traducir_template(request):
    html_original = render_to_string("cuenta.html", {"usuario": request.user})
    html_traducido = traducir_html(html_original, "FR")  # Cambia "FR" por el idioma destino (FR, EN, DE, etc.)
    return HttpResponse(html_traducido)

# Create your views here.
def index(request):
    login_form = AuthenticationForm()
    registro_form = RegistroForm()
    precio = 10000
    tasa_conversion = 0
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
            html_original = render_to_string("index.html", {"usuario": request.user})
            html_traducido = traducir_html(html_original, idioma)  # Cambia "FR" por el idioma destino (FR, EN, DE, etc.)
            return HttpResponse(html_traducido)

    if request.method == "POST":

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
    
    moneda = ""
    productos = Inventario.objects.filter(categoria=categoria)
    if productos == None:
        productos = Inventario.objects.filter(categoria_basica=categoria)
    tasa_conversion = 1  # Por defecto
    carrito = DetalleCarrito.objects.all()
    total = 0

    for i in carrito:
        total+= i.idproducto.precio * i.cantidad
    print(total)

    # ----- TRADUCCIÓN -----
    if 'traduccion' in request.GET:
        idioma = request.GET.get('traduccion')
        html_original = render_to_string("productos.html", {"productos": productos})
        html_traducido = traducir_html(html_original, idioma)
        return HttpResponse(html_traducido)

    # ----- MONEDA Y FORMULARIOS -----
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
        
        if 'addtocart' in request.POST:
            print(f"cantidad: {request.POST.get('product-quantity')}")

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
                git_commit("registro usuario")
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

    # ----- APLICAR TASA A PRODUCTOS -----
    productos_actualizados = []
    for p in productos:
        p.precio_convertido = p.precio * tasa_conversion
        productos_actualizados.append(p)

    paginator = Paginator(productos_actualizados, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    print(f"tasa:{tasa_conversion}, ")
    return render(request, 'productos.html', {
        'productos': productos_actualizados,
        'tasa': tasa_conversion,
        'moneda': moneda if moneda != "" else "CLP",
        'categoria':categoria,
        'total':total,
        'page_obj': page_obj,

    })

def unitario(request, productoID):
    print(productoID)
    producto = Inventario.objects.filter(idproducto = productoID).first()
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
        git_commit("actualizacion perfil")
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
    carrito = DetalleCarrito.objects.all()
    total = 0

    for i in carrito:
        total+= i.idproducto.precio * i.cantidad
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
            
    return render(request, 'resumen.html', {
        })

def pago(request):

    carrito = DetalleCarrito.objects.all()
    total = 0

    for i in carrito:
        total+= i.idproducto.precio * i.cantidad
    print(total)
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
    return render(request, 'pago.html', {'carrito': carrito,
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
            try:
                df = pd.read_excel(archivo_excel)

                for index, row in df.iterrows():
                    idproducto = str(row.get('idproducto')).strip() if pd.notna(row.get('idproducto')) else None
                    nombre = str(row.get('nombre')).strip() if pd.notna(row.get('nombre')) else ''
                    descripcion = str(row.get('descripcion')).strip() if pd.notna(row.get('descripcion')) else ''
                    stock = int(row.get('stock')) if pd.notna(row.get('stock')) else 0
                    precio = int(row.get('precio')) if pd.notna(row.get('precio')) else 0
                    categoria_nombre = str(row.get('categoria')).strip() if pd.notna(row.get('categoria')) else ''

                    if not idproducto or not nombre:
                        continue  # Saltar fila incompleta

                    producto, creado = Inventario.objects.get_or_create(
                        idproducto=idproducto,
                        defaults={
                            'nombre': nombre,
                            'descripcion': descripcion,
                            'stock': stock,
                            'precio': precio,
                            'categoria': categoria_nombre,
                            'alerta': False,
                            'fecha_actualizacion': date.today(),
                            'imagen_base64': '',
                            'precio_convertido': 0,
                            'marca': '',
                        }
                    )

                    if not creado:
                        producto.nombre = nombre
                        producto.descripcion = descripcion
                        producto.stock = stock
                        producto.precio = precio
                        producto.categoria = categoria_nombre
                        producto.fecha_actualizacion = date.today()
                        producto.save()

                messages.success(request, "Archivo procesado correctamente.")
                git_commit("Subida de productos por Excel")
            except Exception as e:
                messages.error(request, f"Error al procesar el archivo: {str(e)}")

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
            git_commit("creación producto")
            return redirect('gestionCatalogo')

        # ✅ EDITAR PRODUCTO
        if 'editar' in request.POST:
            editarCodigo = request.POST.get('editarCodigo')
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
                producto_editado.imagen_base64 = request.POST.get('imageBase64Editada') or ""
                producto_editado.precio_convertido = 0

                producto_editado.save()
                git_commit("edición producto")
            return redirect('gestionCatalogo')

    return render(request, 'gestionCatalogo.html', {'productos': productos})


@login_required
def gestionDescuento(request):
    return render(request, 'gestionDescuento.html')

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
    return render(request, 'gestionReportesAdmin.html')


@login_required
def gestionVenta(request):
    return render(request, 'gestionVenta.html')

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

            git_commit("creacion carrito")

            return redirect('productos/'+ request.POST.get('categoria'))

    return render(request, 'productos.html')


def actualizarCarrito(request):
    
    if request.method == 'POST':
        id_producto = request.POST.get('producto')
        categoria = request.POST.get('categoria')
        operacion = request.POST.get('operacion')
        cliente = Cliente.objects.filter(usuario=request.user.username).first()
        carrito = CarritoCompra.objects.filter(idcliente=cliente.idcliente).first()
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

def borrar(request, productoID):
    producto = Inventario.objects.filter(idproducto = productoID).first()
    producto.delete()
    return redirect('gestionCatalogo')



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
        "ID Pago": pago.idPagoAPI.payment_id,
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

    # Datos de ejemplo
    empresa = "FERREMAS"
    producto = "Cemento 25kg"
    codigo = "CM-25"
    cantidad = 2
    precio_unitario = 12000
    descuento = 10  # %
    subtotal = cantidad * precio_unitario
    total = subtotal * (1 - descuento / 100)
    fecha = datetime.now().strftime('%d/%m/%Y %H:%M')

    # Título
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, height - 40, f"COMPROBANTE DE VENTA - {empresa}")

    # Fecha
    pdf.setFont("Helvetica", 10)
    pdf.drawRightString(width - 40, height - 60, f"Fecha: {fecha}")

    # Detalles de producto
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, height - 100, "Producto:")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(120, height - 100, producto)
    pdf.drawString(40, height - 120, f"Código: {codigo}")
    pdf.drawString(40, height - 140, f"Cantidad: {cantidad}")
    pdf.drawString(40, height - 160, f"Precio Unitario: ${precio_unitario:,}")
    pdf.drawString(40, height - 180, f"Descuento: {descuento}%")
    pdf.drawString(40, height - 200, f"Subtotal: ${subtotal:,}")
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, height - 220, f"Total a Pagar: ${int(total):,}")

    # QR con info de venta
    qr_data = f"{empresa} - Producto: {producto}, Total: ${int(total):,}, Fecha: {fecha}"
    qr_img = qrcode.make(qr_data)

    # Convertimos a formato compatible
    qr_pil = qr_img.convert("RGB")
    qr_io = io.BytesIO()
    qr_pil.save(qr_io, format="PNG")
    qr_io.seek(0)

    # Insertar imagen en el PDF
    pdf.drawInlineImage(Image.open(qr_io), width - 140, height - 260, 100, 100)

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename='comprobante_ferremas.pdf')



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