# -*- coding: utf-8 -*-

# ============================================================
# script.py
#
# PUNTO DE ENTRADA DEL BOTON DE PYREVIT.
# Solo contiene el menu principal y el flujo de cada modo.
# Toda la logica esta en AAC_lib.py (misma carpeta).
# ============================================================

from pyrevit import forms
from AAC_lib import *
import AAC_ui as ui


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================


try:


    # ========================================================
    # SELECCIONAR MODO
    # ========================================================

    modo = ui.elegir_modo(

        [
            "Seleccionar elemento de referencia",
            "Nombrar plataformas segun el suelo",
            "Nombrar topografia/subregion segun la plataforma"
        ],

        mensaje="¿Como quieres seleccionar los elementos?"

    )


    if not modo:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # MODO 1
    # ELEMENTO DE REFERENCIA
    # ========================================================

    if modo == "Seleccionar elemento de referencia":


        # ----------------------------------------------------
        # SELECCIONAR ELEMENTO
        # ----------------------------------------------------

        referencia = uidoc.Selection.PickObject(

            ObjectType.Element,

            "Selecciona un elemento de referencia"

        )


        elemento_referencia = doc.GetElement(
            referencia.ElementId
        )


        if not elemento_referencia:

            raise Exception(
                "No se pudo obtener el elemento seleccionado."
            )


        # ====================================================
        # CATEGORIA
        # ====================================================

        categoria_ref = elemento_referencia.Category


        if not categoria_ref:

            raise Exception(
                "El elemento seleccionado no tiene categoria."
            )


        categoria_id_ref = categoria_ref.Id

        categoria_nombre_ref = categoria_ref.Name


        # ====================================================
        # TIPO
        # ====================================================

        tipo_id_ref = elemento_referencia.GetTypeId()


        # ====================================================
        # SUBPROYECTO
        # ====================================================

        workset_id_ref = elemento_referencia.WorksetId


        # ====================================================
        # FASE
        # ====================================================

        fase_id_ref = elemento_referencia.CreatedPhaseId


        nombre_tipo_ref = obtener_nombre_tipo(
            elemento_referencia
        )


        nombre_workset_ref = obtener_nombre_workset(
            elemento_referencia
        )


        nombre_fase_ref = obtener_nombre_fase(
            elemento_referencia
        )


        # ====================================================
        # BUSCAR COINCIDENCIAS
        # ====================================================

        collector = FilteredElementCollector(doc)\
            .WhereElementIsNotElementType()


        coincidencias = []


        for element in collector:

            try:

                if not element.Category:

                    continue


                misma_categoria = (

                    element.Category.Id.IntegerValue
                    ==
                    categoria_id_ref.IntegerValue

                )


                mismo_tipo = (

                    element.GetTypeId()
                    ==
                    tipo_id_ref

                )


                mismo_workset = (

                    element.WorksetId
                    ==
                    workset_id_ref

                )


                misma_fase = (

                    element.CreatedPhaseId
                    ==
                    fase_id_ref

                )


                if (

                    misma_categoria
                    and mismo_tipo
                    and mismo_workset
                    and misma_fase

                ):

                    coincidencias.append(
                        element
                    )


            except:
                pass


        # ====================================================
        # MOSTRAR INFORMACION
        # ====================================================

        mensaje = (

            "Elemento de referencia detectado:\n\n"

            "Categoria: {}\n"

            "Tipo: {}\n"

            "Subproyecto: {}\n"

            "Fase de creacion: {}\n\n"

            "Coincidencias encontradas: {}"

        ).format(

            categoria_nombre_ref,

            nombre_tipo_ref,

            nombre_workset_ref,

            nombre_fase_ref,

            len(coincidencias)

        )


        continuar = forms.alert(

            mensaje,

            title="AAC BIM Selector",

            yes=True,

            no=True

        )


        if not continuar:

            raise Exception(
                "Operacion cancelada."
            )


        # ====================================================
        # SELECCIONAR EN REVIT
        # ====================================================

        ids = List[ElementId]()


        for element in coincidencias:

            ids.Add(
                element.Id
            )


        uidoc.Selection.SetElementIds(
            ids
        )


        # ====================================================
        # PREGUNTAR SI QUIERE NOMBRAR
        # ====================================================

        nombrar = forms.alert(

            "{} elementos seleccionados.\n\n"
            "¿Quieres nombrarlos ahora?".format(
                len(coincidencias)
            ),

            title="AAC BIM Selector",

            yes=True,

            no=True

        )


        if nombrar:

            nombrar_elementos(
                coincidencias
            )


    # ========================================================
    # MODO 2
    # NOMBRAR PLATAFORMAS SEGUN EL SUELO
    # ========================================================

    elif modo == "Nombrar plataformas segun el suelo":

        nombrar_plataformas_segun_suelo()


    # ========================================================
    # MODO 3
    # NOMBRAR TOPOGRAFIA/SUBREGION SEGUN LA PLATAFORMA
    # ========================================================

    elif modo == "Nombrar topografia/subregion segun la plataforma":

        nombrar_topografia_segun_plataforma()


# ============================================================
# ERRORES
# ============================================================

except Exception as error:


    if str(error) != "Operacion cancelada.":


        forms.alert(

            "Ocurrio un error:\n\n{}".format(
                error
            ),

            title="AAC BIM Selector - ERROR"

        )