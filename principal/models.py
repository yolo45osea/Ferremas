from decimal import Decimal
import uuid
from django.urls import reverse
from payments import PurchasedItem
from payments.models import BasePayment
from pagos.models import Payment as Pagos
from django.db import models

class Payment(BasePayment):
    # Cambiar el campo pk para que sea un UUID
    #payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    def get_failure_url(self) -> str:
        return reverse('payment_failure', kwargs={'pk': self.pk})

    def get_success_url(self) -> str:
        return reverse('payment_success', kwargs={'pk': self.pk})

class Administrador(models.Model):
    idadmin = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=25)
    nombre = models.CharField(max_length=25)
    apellido = models.CharField(max_length=25)
    rut = models.CharField(max_length=12, unique=True)
    correo = models.EmailField(max_length=50, unique=True)
    contrasena = models.CharField(max_length=25)
    telefono = models.CharField(max_length=12)

class Cliente(models.Model):
    idcliente = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=25)
    nombre = models.CharField(max_length=25)
    apellido = models.CharField(max_length=25)
    rut = models.CharField(max_length=12, unique=True)
    correo = models.EmailField(max_length=50, unique=True)
    contrasena = models.CharField(max_length=25)
    direccion = models.TextField()
    telefono = models.CharField(max_length=20)
    fecha_registro = models.DateField()

    def __str__(self):
        return f"{self.nombre} ({self.correo})"

class Contador(models.Model):
    idcontador = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=25)
    apellido = models.CharField(max_length=25)
    rut = models.CharField(max_length=12)
    correo = models.EmailField(max_length=50)
    contrasena = models.CharField(max_length=25)
    telefono = models.CharField(max_length=12)

class CarritoCompra(models.Model):
    idcarrito = models.AutoField(primary_key=True)
    idcliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)  # para invitados
    fechacreacion = models.DateField()
    estado = models.BooleanField()

class Inventario(models.Model):
    idproducto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255)
    marca = models.CharField(max_length=50)
    categoria = models.CharField(max_length=25)
    precio = models.IntegerField()
    precio_convertido = models.IntegerField()
    imagen_base64 = models.TextField(blank=True, null=True)
    stock = models.IntegerField()
    alerta = models.BooleanField()
    fecha_actualizacion = models.DateField()

class DetalleCarrito(models.Model):
    idcarritoprod = models.AutoField(primary_key=True)
    idcarrito = models.ForeignKey(CarritoCompra, on_delete=models.CASCADE)
    idproducto = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    cantidad = models.IntegerField()

    def total(self):
        return self.idproducto.precio * self.cantidad

class Informe(models.Model):
    idinforme = models.AutoField(primary_key=True)
    idcontador = models.ForeignKey(Contador, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=50)
    fecha_creacion = models.DateField()
    descripcion = models.CharField(max_length=100)









class Pago(models.Model):
    idPagoAPI = models.ForeignKey(Pagos, on_delete=models.CASCADE, primary_key=True)
    idcliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)


class Descuento(models.Model):
    nombreDescuento = models.CharField(max_length=25)
    codigo = models.CharField(max_length=25, primary_key=True)
    descuento = models.IntegerField()
    fechaInicio = models.DateTimeField()
    fechaTermino = models.DateTimeField()
    estado = models.BooleanField()







class Sucursal(models.Model):
    idSucursal = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=25)
    direccion = models.CharField(max_length=50, null=True, blank=True)



class Vendedor(models.Model):
    idvendedor = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=25)
    nombre = models.CharField(max_length=25)
    apellido = models.CharField(max_length=25)
    rut = models.CharField(max_length=12)
    correo = models.EmailField(max_length=50)
    contrasena = models.CharField(max_length=25)
    idadmin = models.ForeignKey(Administrador, on_delete=models.CASCADE)
    zona = models.ForeignKey(Sucursal, on_delete=models.CASCADE)


class Pedido(models.Model):
    idpedido = models.AutoField(primary_key=True)
    idcliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    idvendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, null=True, blank=True)
    idPagoAPI = models.ForeignKey(Pagos, on_delete=models.CASCADE)
    productos = models.JSONField()
    fecha_pedido = models.DateField()
    estado = models.CharField(max_length=10)
    tipo_entrega = models.CharField(max_length=9)
    direccion_entrega = models.CharField(max_length=50, null=True, blank=True)
    fecha_estimada = models.DateField()
    notificado = models.BooleanField()
    notificado_cliente = models.BooleanField(default=0)


class Venta(models.Model):
    idcarrito = models.AutoField(primary_key=True)
    idvendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, null=True, blank=True)
    fechacreacion = models.DateField()
    estado = models.BooleanField()


class DetalleVenta(models.Model):
    idventaprod = models.AutoField(primary_key=True)
    idventa = models.ForeignKey(Venta, on_delete=models.CASCADE)
    idproducto = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    #total = models.IntegerField()

    def total(self):
        return self.idproducto.precio * self.cantidad
    

class Bodeguero(models.Model):
    idbodeguero = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=25)
    nombre = models.CharField(max_length=25)
    apellido = models.CharField(max_length=25)
    rut = models.CharField(max_length=12)
    correo = models.EmailField(max_length=50)
    contrasena = models.CharField(max_length=25)
    idadmin = models.ForeignKey(Administrador, on_delete=models.CASCADE)
    zona = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    
class Notificacion(models.Model):
    idnotificacion = models.AutoField(primary_key=True)
    idcliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    idvendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, null=True, blank=True)
    idbodeguero = models.ForeignKey(Bodeguero, on_delete=models.CASCADE, null=True, blank=True)
    mensaje = models.CharField(max_length=100)
    fecha_envio = models.DateField()
    leido = models.BooleanField()
