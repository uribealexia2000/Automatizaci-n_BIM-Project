# -*- coding: utf-8 -*-

# ============================================================
# AAC_ui.py
#
# CAPA DE PRESENTACION.
#
# Funciones que envuelven pyrevit.forms para mantener un
# estilo consistente en todas las ventanas del proyecto:
# mismo prefijo de titulo, mismo ancho de listas, mismos
# iconos. No contiene logica de negocio ni toca el modelo
# de Revit — solo arma texto y llama a pyrevit.forms.
#
# Este archivo es ADITIVO: no reemplaza ni modifica ninguna
# funcion existente en AAC_lib.py. Se puede adoptar de a
# poco, funcion por funcion.
# ============================================================

from pyrevit import forms


NOMBRE_APP = "AAC BIM Selector"

ANCHO_LISTA_DEFECTO = 500


def _titulo(subtitulo=None):

    if subtitulo:

        return "{} - {}".format(
            NOMBRE_APP,
            subtitulo
        )

    return NOMBRE_APP


# ============================================================
# MENU DE MODOS (CommandSwitchWindow)
# ============================================================


def elegir_modo(opciones, mensaje):

    return forms.CommandSwitchWindow.show(

        opciones,

        message=mensaje

    )


# ============================================================
# LISTA DE SELECCION (SelectFromList)
# ============================================================


def elegir_lista(

    opciones,
    subtitulo,
    boton="Siguiente",
    multiselect=False,
    ancho=ANCHO_LISTA_DEFECTO

):

    return forms.SelectFromList.show(

        opciones,

        title=_titulo(subtitulo),

        button_name=boton,

        multiselect=multiselect,

        width=ancho

    )


# ============================================================
# TEXTO LIBRE (ask_for_string)
# ============================================================


def pedir_texto(mensaje, subtitulo, valor_defecto=""):

    return forms.ask_for_string(

        default=valor_defecto,

        prompt=mensaje,

        title=_titulo(subtitulo)

    )


# ============================================================
# ALERTAS
# ============================================================


def confirmar(mensaje, subtitulo=None, icono_alerta=False):

    """
    Alerta con botones Si/No. Devuelve True/False.
    icono_alerta=False por defecto: no es un error, es una
    confirmacion normal, asi que no se ve tan alarmante.
    """

    return forms.alert(

        mensaje,

        title=_titulo(subtitulo),

        yes=True,

        no=True,

        warn_icon=icono_alerta

    )


def avisar(mensaje, subtitulo=None, icono_alerta=True):

    """
    Alerta informativa con un solo boton (Aceptar).
    icono_alerta=True por defecto: la mayoria de los avisos
    son advertencias o resultados que conviene resaltar.
    """

    forms.alert(

        mensaje,

        title=_titulo(subtitulo),

        warn_icon=icono_alerta

    )
