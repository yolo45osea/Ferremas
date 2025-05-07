from typing import Any, Optional

from django.urls import reverse, NoReverseMatch
import requests
from django.http import JsonResponse
from payments import PaymentError, PaymentStatus, RedirectNeeded
from payments.core import BasicProvider
from payments.forms import PaymentForm as BasePaymentForm
import logging


logger = logging.getLogger(__name__)

vci_status = {
    "TSY": "Autenticación Exitosa",
    "TSN": "Autenticación Rechazada",
    "NP": "No Participa, sin autenticación",
    "U3": "Falla conexión, Autenticación Rechazada",
    "INV": "Datos Inválidos",
    "A": "Intentó",
    "CNP1": "Comercio no participa",
    "EOP": "Error operacional",
    "BNA": "BIN no adherido",
    "ENA": "Emisor no adherido",
    "TSYS": "Autenticación exitosa Sin fricción. Resultado autenticación: Autenticación Existosa",
    "TSAS": "Intento, tarjeta no enrolada / emisor no disponible. Resultado autenticación: Autenticación Exitosa",
    "TSNS": "Fallido, no autenticado, denegado / no permite intentos. Resultado autenticación: Autenticación denegada",
    "TSRS": "Autenticación rechazada - sin fricción. Resultado autenticación: Autenticación rechazada",
    "TSUS": "Autenticación no se pudo realizar por problema técnico u otro motivo. Resultado autenticación: \
        Autenticación fallida",
    "TSCF": "Autenticación con fricción(No aceptada por el comercio). Resultado autenticación: Autenticación \
        incompleta",
    "TSYF": "Autenticación exitosa con fricción. Resultado autenticación: Autenticación exitosa",
    "TSNF": "No autenticado. Transacción denegada con fricción. Resultado autenticación: Autenticación denegada",
    "TSUF": "Autenticación con fricción no se pudo realizar por problema técnico u otro. Resultado autenticación: \
        Autenticación fallida",
    "NPC": "Comercio no Participa. Resultado autenticación: Comercio/BIN no participa",
    "NPB": "BIN no participa. Resultado autenticación: Comercio/BIN no participa",
    "NPCB": "Comercio y BIN no participan. Resultado autenticación: Comercio/BIN no participa",
    "SPCB": "Comercio y BIN sí participan. Resultado autenticación: Autorización incompleta",
}

tipo_de_pagos = {
    "VD": "Venta Débito.",
    "VN": "Venta Normal.",
    "VC": "Venta en cuotas.",
    "SI": "3 cuotas sin interés.",
    "S2": "2 cuotas sin interés.",
    "NC": "N Cuotas sin interés",
    "VP": "Venta Prepago.",
}

codigos_rechazo_nivel_1 = {
    "-1": "Rechazo - Posible error en el ingreso de datos de la transacción",
    "-2": "Rechazo - Se produjo fallo al procesar la transacción, este mensaje de rechazo se encuentra relacionado \
        a parámetros de la tarjeta y/o su cuenta asociada",
    "-3": "Rechazo - Error en Transacción",
    "-4": "Rechazo - Rechazada por parte del emisor",
    "-5": "Rechazo - Transacción con riesgo de posible fraude",
}

codigo_rechazo_refund = {
    "304": "Validación de campos de entrada nulos",
    "245": "Código de comercio no existe",
    "22": "El comercio no se encuentra activo",
    "316": "El comercio indicado no corresponde al certificado o no es hijo del comercio MALL en caso de \
        transacciones MALL",
    "308": "Operación no permitida",
    "274": "Transacción no encontrada",
    "16": "La transacción no permite anulación",
    "292": "La transacción no está autorizada",
    "284": "Periodo de anulación excedido",
    "310": "Transacción anulada previamente",
    "311": "Monto a anular excede el saldo disponible para anular",
    "312": "Error genérico para anulaciones",
    "315": "Error del autorizador",
    "53": "La transacción no permite anulación parcial de transacciones con cuotas",
}


class WebpayProvider(BasicProvider):
    """
    WebpayProvider es una clase que proporciona integración con Transbank para procesar pagos.
    Inicializa una instancia de WebpayProvider con el key y el secreto de Transbank.

    Args:
        api_key_id (str): ApiKey entregada por Transbank.
        api_key_secret (str): ApiSecret entregada por Transbank.
        api_endpoint (str): Ambiente Transbank, puede ser "produccion" o "integracion" (Valor por defecto: produccion)
        **kwargs: Argumentos adicionales.
    """

    form_class = BasePaymentForm
    api_endpoint: str
    api_key_id: str = None
    api_key_secret: str = None

    def __init__(
        self,
        api_key_id: str,
        api_key_secret: str,
        api_endpoint: str = "produccion",
        **kwargs: int,
    ):
        super().__init__(**kwargs)
        self.api_endpoint = api_endpoint
        self.api_key_id = api_key_id
        self.api_key_secret = api_key_secret
        if self.api_endpoint == "produccion":
            self.api_endpoint = "https://webpay3g.transbank.cl/"
        elif self.api_endpoint == "integracion":
            self.api_endpoint = "https://webpay3gint.transbank.cl/"

    def get_form(self, payment, data: Optional[dict] = None) -> Any:
        """
        Genera el formulario de pago para redirigir a la página de pago.

        Args:
            payment ("Payment"): Objeto de pago Django Payments.
            data (dict | None): Datos del formulario (opcional).

        Returns:
            Any: Formulario de pago redirigido a la página de pago.

        Raises:
            RedirectNeeded: Redirige a la página de pago.
        """
        if not payment.transaction_id:
            token = str(payment.token).replace("-", "")[:26]
            datos_para_tbk = {
                "buy_order": token,
                "session_id": token,
                "return_url": payment.get_process_url(),
                "amount": int(payment.total),
            }

            try:
                # Solicitar la creación del pago en Webpay
                pago_req = requests.post(
                    f"{self.api_endpoint}rswebpaytransaction/api/webpay/v1.2/transactions",
                    json=datos_para_tbk,
                    headers=self.genera_headers(),
                    timeout=5,
                )
                # Lanzar una excepción si la respuesta es un error
                pago_req.raise_for_status()

            except requests.exceptions.RequestException as e:
                logger.info(f"return_url: {payment.get_process_url()}")
                logger.error(f"Error en la solicitud a Webpay: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    logger.error(f"Status Code: {e.response.status_code}")
                    logger.error(f"Headers: {e.response.headers}")
                    logger.error(f"Respuesta de Webpay: {e.response.text}")
                payment.change_status(PaymentStatus.ERROR, str(e))
                raise PaymentError(f"Error al procesar el pago: {str(e)}")

            else:
                # Si la solicitud es exitosa, procesar la respuesta de Webpay
                pago = pago_req.json()
                payment.transaction_id = pago["token"]
                payment.attrs.request_tbk = datos_para_tbk
                payment.attrs.respuesta_tbk = pago
                payment.save()
                payment.change_status(PaymentStatus.PREAUTH)

            # Redirigir al cliente a Webpay para completar el pago
            raise RedirectNeeded(f"{pago['url']}?token_ws={pago['token']}")

    def genera_headers(self):
        
        return {
            "Content-Type": "application/json",
            "Tbk-Api-Key-Id": self.api_key_id,
            "Tbk-Api-Key-Secret": self.api_key_secret,
        }

    def process_data(self, payment, request) -> JsonResponse:
        """
        Procesa la captura del pago
        Usuario deberia volver acá y luego a la pagina de muestra de informacion.
        """

        if payment.status in [PaymentStatus.WAITING, PaymentStatus.PREAUTH]:
            self.commit(self.get_token_from_request(request, payment), payment)

        # Redirigir al usuario a una página de éxito
        raise RedirectNeeded('/success/')

    def get_token_from_request(self, request, payment) -> str:
        """Return payment token from provider request."""
        
        # Intentar obtener el 'token_ws' desde POST o GET usando el método `get()` para evitar excepciones
        token_ws = request.POST.get("token_ws") or request.GET.get("token_ws")
        
        # Si no se encuentra el token_ws, lanzar un error con mensaje claro
        if not token_ws:
            raise PaymentError(
                code=400,
                message="token_ws is not present in the request."
            )
        
        return token_ws

    def actualiza_estado(self, payment) -> dict:
        """Actualiza el estado del pago con Flow

        Args:
            payment ("Payment): Objeto de pago Django Payments.

        Returns:
            dict: Diccionario con valores del objeto `PaymentStatus`.
        """

        try:
            status_req = requests.put(
                f"{self.api_endpoint}/rswebpaytransaction/api/webpay/v1.2/transactions/{payment.token}",
                timeout=5,
                headers=self.genera_headers(),
            )
            status_req.raise_for_status()
        except Exception as e:
            raise e
        else:
            status = status_req.json()
            payment.attrs.status_response = status
            payment.save()

            if status["response_code"] == 0:
                payment.change_status(PaymentStatus.CONFIRMED)
                return PaymentStatus.CONFIRMED
            else:
                payment.change_status(PaymentStatus.REJECTED)
                return PaymentStatus.REJECTED

    def commit(self, token, payment):
        """Se debe llamar al procesar el retorno"""
        try:
            commit_req = requests.put(
                f"{self.api_endpoint}/rswebpaytransaction/api/webpay/v1.2/transactions/{token}",
                timeout=5,
                headers=self.genera_headers(),
            )
            commit_req.raise_for_status()
        except Exception as e:
            raise e
        else:
            commit = commit_req.json()
            commit["vci_str"] = self.agrega_info_error("vci", commit["vci"])
            commit["payment_type_code_str"] = self.agrega_info_error("pago", commit["payment_type_code"])
            payment.attrs.commit_response = commit
            payment.save()

            # Verificar el estado de la transacción
            if commit["status"] == "AUTHORIZED" and commit["response_code"] == 0:
                # Redirigir a la página de éxito si está autorizado
                try:
                    redirect_url = reverse('payment_success')
                except NoReverseMatch:
                    print("🔴 No se encontró la URL 'payment_success'")
                    redirect_url = 'http://localhost:8000/success'  # temporal
            elif commit["status"] == "PREAUTH":
                # Si el estado es PREAUTH, informar que el pago está pendiente
                redirect_url = reverse('payment_pending')
            else:
                # Redirigir a la página de error en otros casos
                redirect_url = reverse('payment_failure')

            raise RedirectNeeded(redirect_url)    
    
    def refund(self, payment, amount: Optional[int] = None) -> int:
        """
        Realiza un reembolso del pago.
        El seguimiendo se debe hacer directamente en Flow

        Args:
            payment ("Payment"): Objeto de pago Django Payments.
            amount (int | None): Monto a reembolsar (opcional).

        Returns:
            int: Monto de reembolso solicitado.

        Raises:
            PaymentError: Error al crear el reembolso.

        """
        if payment.status != PaymentStatus.CONFIRMED:
            raise PaymentError("El pago debe estar confirmado para reversarse.")

        refund_data = {"amount": amount or payment.total}
        try:
            refund_req = requests.put(
                f"{self.api_endpoint}/rswebpaytransaction/api/webpay/v1.2/transactions/{payment.token}/refunds",
                timeout=5,
                headers=self.genera_headers(),
                data=refund_data,
            )
            refund_req.raise_for_status()
        except Exception as e:
            raise e
        else:
            refund = refund_req.json()
            refund["response_code_str"] = self.agrega_info_error("refund", refund["response_code"])
            payment.attrs.refund_response = refund
            payment.save()

            if refund["type"] == "REVERSED":
                payment.change_status(PaymentStatus.REFUNDED)
                return payment.total
            elif refund["type"] == "NULLIFIED" and refund["response_code"] == 0:
                payment.change_status(PaymentStatus.REFUNDED)
                return refund["nullified_amount"]

    def agrega_info_error(self, tipo, codigo):
        if tipo == "vci":
            return vci_status.get(codigo, None)
        elif tipo == "pago":
            return tipo_de_pagos.get(codigo, None)
        elif tipo == "rechazo_l1":
            return codigos_rechazo_nivel_1.get(codigo, None)
        elif tipo == "refund":
            return codigo_rechazo_refund.get(codigo, None)
        else:
            return None
