# signals.py
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from .models import Vendedor, Administrador  # Asegúrate de importar tu modelo Administrador

@receiver(m2m_changed, sender=User.groups.through)
def crear_vendedor_si_es_vendedor(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        try:
            grupo_vendedor = Group.objects.get(name="vendedores")
        except Group.DoesNotExist:
            return

        if grupo_vendedor.pk in pk_set:
            if not Vendedor.objects.filter(usuario=instance.username).exists():
                # Aquí puedes definir cómo obtener el administrador actual
                administrador = User.objects.filter(is_superuser=1).first()
                if Administrador.objects.filter(usuario= administrador.username).exists():
                    admin = Administrador.objects.get(usuario=administrador.username)
                else:
                    admin = Administrador.objects.create(
                        usuario=administrador.username,
                        nombre=administrador.first_name,
                        apellido=administrador.last_name,
                        rut="",  # o lo puedes dejar vacío y editar después
                        correo=administrador.email,
                        contrasena=administrador.password,  # OJO: es hash, no el texto plano
                        telefono=""
                    )

                Vendedor.objects.create(
                    usuario=instance.username,
                    nombre=instance.first_name,
                    apellido=instance.last_name,
                    rut="",  # o lo puedes dejar vacío y editar después
                    correo=instance.email,
                    contrasena=instance.password,  # OJO: es hash, no el texto plano
                    idadmin=admin,
                    zona=1  # o puedes poner un valor predeterminado
                )
