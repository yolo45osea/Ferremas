from django import template

register = template.Library()

@register.filter
def formatear_pesos(valor):
    try:
        valor = float(valor)
        valor_formateado = "{:,.2f}".format(valor)
        return valor_formateado.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return valor
