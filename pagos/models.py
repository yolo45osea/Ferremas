from decimal import Decimal
import uuid
from django.urls import reverse
from payments import PurchasedItem
from payments.models import BasePayment
from django.db import models

class Payment(BasePayment):
    # Cambiar el campo pk para que sea un UUID
    id = models.AutoField(primary_key=True)
    tipo_documento = models.TextField(blank=True, null=True)

    def get_failure_url(self) -> str:
        return reverse('payment_failure', kwargs={'pk': self.pk})

    def get_success_url(self) -> str:
        return reverse('payment_success', kwargs={'pk': self.pk})