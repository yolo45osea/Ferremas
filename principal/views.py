from datetime import date
from django.http import JsonResponse
from django.shortcuts import render
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
from principal.models import Cliente, Inventario
from .utilities import traducir_html
from django.template.loader import render_to_string


logger = logging.getLogger(__name__)

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

    if request.user.groups.filter(name='vendedores').exists():
        tipo_usuario = 'vendedor'
    else:
        tipo_usuario = 'contador'

    print(f"tipo de usuario: {tipo_usuario}")


    if request.method == "GET":
        if 'traduccion' in request.GET:
            idioma = request.GET.get('traduccion')
            print(f"idioma: {idioma}")
            html_original = render_to_string("index.html", {"usuario": request.user})
            html_traducido = traducir_html(html_original, idioma)  # Cambia "FR" por el idioma destino (FR, EN, DE, etc.)
            return HttpResponse(html_traducido)

    if request.method == "POST":
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
                    rut = "",
                    correo = request.POST.get('email'),
                    contrasena = request.POST.get('password1'),
                    direccion = "",
                    telefono = "",
                    fecha_registro = date.today()
                )
                login(request, user)
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
    return render(request, 'index.html', {'precio': precio * tasa_conversion if tasa_conversion>0 else precio, 'login_form': login_form, 
                   'registro_form': registro_form, 'tipo_usuario': tipo_usuario, 'idioma': idioma})



def productos(request, categoria):
    moneda = ""
    productos = Inventario.objects.filter(categoria=categoria)
    tasa_conversion = 1  # Por defecto

    # ----- TRADUCCIÓN -----
    if 'traduccion' in request.GET:
        idioma = request.GET.get('traduccion')
        html_original = render_to_string("productos.html", {"productos": productos})
        html_traducido = traducir_html(html_original, idioma)
        return HttpResponse(html_traducido)

    # ----- MONEDA Y FORMULARIOS -----
    if request.method == "POST":
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


    print(f"tasa:{tasa_conversion}, ")
    return render(request, 'productos.html', {
        'productos': productos_actualizados,
        'tasa': tasa_conversion,
        'moneda': moneda if moneda != "" else "CLP"

    })

def detail(request):
    return render(request, 'detail.html')

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
        return redirect('cuenta')
    
    return render(request, 'cuenta.html', {'usuario': usuario, 'tipo_usuario':tipo_usuario})

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
    return render(request, 'resumen.html')

def pago(request):
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
    return render(request, 'pago.html')


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
    return render(request, 'base.html')

def contacto(request):
    return render(request, 'contacto.html')

@login_required
def gestionCatalogo(request):
    productos = Inventario.objects.all()
    print(productos)
    return render(request, 'gestionCatalogo.html', {'productos':productos})

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
    return render(request, 'gestionPagos.html')

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
