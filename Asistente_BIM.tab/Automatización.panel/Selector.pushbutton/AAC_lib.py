# -*- coding: utf-8 -*-

# ============================================================
# AAC_lib.py
#
# LIBRERIA CON TODAS LAS FUNCIONES DEL SELECTOR/NOMBRADOR BIM.
# NO SE EJECUTA DIRECTAMENTE COMO COMANDO DE REVIT: la usa
# script.py, que esta en la misma carpeta, mediante:
#
#     from AAC_lib import *
#
# ============================================================

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    ElementId,
    BuiltInParameter,
    StorageType,
    Transaction,
    Line,
    XYZ
)

from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException

from System.Collections.Generic import List
from pyrevit import forms


# ============================================================
# DOCUMENTO ACTIVO
#
# Se obtiene via pyrevit.revit en vez de __revit__ directo,
# para que este modulo funcione tanto si se ejecuta como
# comando como si se importa desde otro script (script.py).
# ============================================================

from pyrevit import revit

uidoc = revit.uidoc
doc = revit.doc


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================


# ============================================================
# SELECCIONAR Y FORZAR ZOOM A UN GRUPO DE ELEMENTOS
#
# uidoc.ShowElements a veces no mueve la vista si Revit
# considera que "ya se puede ver" el elemento (aunque este
# fuera de la parte visible en pantalla). Por eso, ademas,
# se calcula el rectangulo que envuelve a todos los elementos
# y se fuerza el zoom con ZoomAndCenterRectangle.
# ============================================================


def _enfocar_elementos(elementos):

    if not elementos:
        return


    ids = List[ElementId]()

    for element in elementos:
        ids.Add(element.Id)


    uidoc.Selection.SetElementIds(
        ids
    )


    try:
        uidoc.ShowElements(ids)
    except:
        pass


    # ========================================================
    # CALCULAR EL RECTANGULO QUE ENVUELVE A TODOS
    # ========================================================

    x_min = x_max = y_min = y_max = z_min = z_max = None


    for element in elementos:

        bbox = element.get_BoundingBox(doc.ActiveView)

        if not bbox:
            bbox = element.get_BoundingBox(None)

        if not bbox:
            continue


        if x_min is None:

            x_min, y_min, z_min = bbox.Min.X, bbox.Min.Y, bbox.Min.Z
            x_max, y_max, z_max = bbox.Max.X, bbox.Max.Y, bbox.Max.Z


        else:

            x_min = min(x_min, bbox.Min.X)
            y_min = min(y_min, bbox.Min.Y)
            z_min = min(z_min, bbox.Min.Z)

            x_max = max(x_max, bbox.Max.X)
            y_max = max(y_max, bbox.Max.Y)
            z_max = max(z_max, bbox.Max.Z)


    if x_min is None:
        return


    # ========================================================
    # UN POCO DE MARGEN ALREDEDOR (EN PIES)
    # ========================================================

    margen = 10.0

    punto_min = XYZ(x_min - margen, y_min - margen, z_min)
    punto_max = XYZ(x_max + margen, y_max + margen, z_max)


    try:

        for vista_ui in uidoc.GetOpenUIViews():

            if vista_ui.ViewId == doc.ActiveView.Id:

                vista_ui.ZoomAndCenterRectangle(
                    punto_min,
                    punto_max
                )

                break


    except Exception as error:

        print(
            "No se pudo hacer zoom automatico: {}".format(
                error
            )
        )


def obtener_nombre_tipo(element):

    nombre_tipo = "Sin tipo"

    try:

        type_id = element.GetTypeId()

        if type_id != ElementId.InvalidElementId:

            tipo = doc.GetElement(type_id)

            if tipo:

                parametro_tipo = tipo.get_Parameter(
                    BuiltInParameter.SYMBOL_NAME_PARAM
                )

                if parametro_tipo:

                    valor = parametro_tipo.AsString()

                    if valor:
                        nombre_tipo = valor

    except:
        pass

    return nombre_tipo


# ============================================================


def obtener_nombre_fase(element):

    nombre_fase = "Sin fase"

    try:

        fase_id = element.CreatedPhaseId

        if fase_id != ElementId.InvalidElementId:

            fase = doc.GetElement(
                fase_id
            )

            if fase:
                nombre_fase = fase.Name

    except:
        pass

    return nombre_fase


# ============================================================


def obtener_nombre_workset(element):

    nombre_workset = "Sin subproyecto"

    try:

        workset_table = doc.GetWorksetTable()

        workset = workset_table.GetWorkset(
            element.WorksetId
        )

        if workset:
            nombre_workset = workset.Name

    except:
        pass

    return nombre_workset


# ============================================================
# OBTENER PARAMETROS DE TEXTO EDITABLES
# COMUNES A TODOS LOS ELEMENTOS
# ============================================================


def obtener_parametros_texto_comunes(elementos):

    if not elementos:
        return []

    parametros_comunes = None


    for element in elementos:

        parametros_elemento = set()


        for parametro in element.Parameters:

            try:

                if not parametro.Definition:
                    continue


                nombre = parametro.Definition.Name


                if not nombre:
                    continue


                if parametro.IsReadOnly:
                    continue


                if parametro.StorageType != StorageType.String:
                    continue


                parametros_elemento.add(
                    nombre
                )


            except:
                pass


        if parametros_comunes is None:

            parametros_comunes = parametros_elemento


        else:

            parametros_comunes = parametros_comunes.intersection(
                parametros_elemento
            )


    if not parametros_comunes:
        return []


    resultado = list(
        parametros_comunes
    )

    resultado.sort()

    return resultado


# ============================================================
# BOUNDING BOX EN COORDENADAS DE MODELO (MUNDO)
#
# Se usa para saber si una plataforma esta dentro de un suelo,
# sin depender de la vista activa.
# ============================================================


def obtener_bbox_mundial(element):

    try:

        bbox = element.get_BoundingBox(None)

        if not bbox:
            return None

        return {
            "x_min": bbox.Min.X,
            "x_max": bbox.Max.X,
            "y_min": bbox.Min.Y,
            "y_max": bbox.Max.Y,
            "z_min": bbox.Min.Z,
            "z_max": bbox.Max.Z
        }

    except:
        return None


# ============================================================
# SOLAPE EN PLANTA (X-Y) ENTRE DOS BOUNDING BOX
#
# Devuelve un valor entre 0 y 1, relativo al area del
# elemento MAS PEQUEÑO de los dos (util para saber que tan
# "contenida" esta una plataforma dentro de un suelo).
# ============================================================


def calcular_solape_xy(bbox1, bbox2):

    ancho_solape = (
        min(bbox1["x_max"], bbox2["x_max"])
        - max(bbox1["x_min"], bbox2["x_min"])
    )

    alto_solape = (
        min(bbox1["y_max"], bbox2["y_max"])
        - max(bbox1["y_min"], bbox2["y_min"])
    )

    if ancho_solape <= 0 or alto_solape <= 0:
        return 0.0

    area_solape = ancho_solape * alto_solape

    area1 = (
        (bbox1["x_max"] - bbox1["x_min"])
        * (bbox1["y_max"] - bbox1["y_min"])
    )

    area2 = (
        (bbox2["x_max"] - bbox2["x_min"])
        * (bbox2["y_max"] - bbox2["y_min"])
    )

    area_menor = min(area1, area2)

    if area_menor <= 0:
        return 0.0

    return area_solape / area_menor


# ============================================================
# LETRA A PARTIR DE UN INDICE (0 -> A, 1 -> B ... 25 -> Z,
# 26 -> AA, 27 -> AB ...)
# ============================================================


def _letra_desde_indice(indice):

    n = indice + 1

    letras = ""


    while n > 0:

        n, resto = divmod(n - 1, 26)

        letras = chr(65 + resto) + letras


    return letras


# ============================================================
# ORDEN ESPACIAL
#
# SUPERIOR IZQUIERDA
# ->
# DERECHA
# ->
# CONTINUAR HACIA ABAJO
#
# SEGUN LA VISTA ACTIVA
# ============================================================


def _calcular_datos_elementos(elementos):

    vista = doc.ActiveView

    derecha = vista.RightDirection
    arriba = vista.UpDirection

    datos = []


    # ========================================================
    # OBTENER POSICION Y EXTENSION
    # DE CADA ELEMENTO
    # ========================================================

    for element in elementos:

        try:

            bbox = element.get_BoundingBox(
                vista
            )


            # Si por alguna razon no funciona
            # con la vista activa, usamos el
            # BoundingBox general.

            if not bbox:

                bbox = element.get_BoundingBox(
                    None
                )


            if not bbox:

                print(
                    "ID {} sin BoundingBox.".format(
                        element.Id.IntegerValue
                    )
                )

                continue


            # ------------------------------------------------
            # CENTRO
            # ------------------------------------------------

            centro_x = (
                bbox.Min.X + bbox.Max.X
            ) / 2.0


            centro_y = (
                bbox.Min.Y + bbox.Max.Y
            ) / 2.0


            centro_z = (
                bbox.Min.Z + bbox.Max.Z
            ) / 2.0


            # ------------------------------------------------
            # POSICION HORIZONTAL SEGUN LA VISTA
            # ------------------------------------------------

            posicion_x = (

                centro_x * derecha.X
                +
                centro_y * derecha.Y
                +
                centro_z * derecha.Z

            )


            # ------------------------------------------------
            # POSICION VERTICAL SEGUN LA VISTA
            # ------------------------------------------------

            posicion_y = (

                centro_x * arriba.X
                +
                centro_y * arriba.Y
                +
                centro_z * arriba.Z

            )


            # ------------------------------------------------
            # ESQUINAS DEL BOUNDING BOX
            # ------------------------------------------------

            esquinas = [

                (
                    bbox.Min.X,
                    bbox.Min.Y,
                    bbox.Min.Z
                ),

                (
                    bbox.Min.X,
                    bbox.Min.Y,
                    bbox.Max.Z
                ),

                (
                    bbox.Min.X,
                    bbox.Max.Y,
                    bbox.Min.Z
                ),

                (
                    bbox.Min.X,
                    bbox.Max.Y,
                    bbox.Max.Z
                ),

                (
                    bbox.Max.X,
                    bbox.Min.Y,
                    bbox.Min.Z
                ),

                (
                    bbox.Max.X,
                    bbox.Min.Y,
                    bbox.Max.Z
                ),

                (
                    bbox.Max.X,
                    bbox.Max.Y,
                    bbox.Min.Z
                ),

                (
                    bbox.Max.X,
                    bbox.Max.Y,
                    bbox.Max.Z
                )

            ]


            valores_x = []
            valores_y = []


            # ------------------------------------------------
            # PROYECTAR ESQUINAS
            # SEGUN LA ORIENTACION DE LA VISTA
            # ------------------------------------------------

            for x, y, z in esquinas:


                valor_x = (

                    x * derecha.X
                    +
                    y * derecha.Y
                    +
                    z * derecha.Z

                )


                valor_y = (

                    x * arriba.X
                    +
                    y * arriba.Y
                    +
                    z * arriba.Z

                )


                valores_x.append(
                    valor_x
                )

                valores_y.append(
                    valor_y
                )


            x_min = min(
                valores_x
            )

            x_max = max(
                valores_x
            )

            y_min = min(
                valores_y
            )

            y_max = max(
                valores_y
            )


            datos.append(
                {
                    "elemento": element,
                    "x": posicion_x,
                    "y": posicion_y,
                    "x_min": x_min,
                    "x_max": x_max,
                    "y_min": y_min,
                    "y_max": y_max
                }
            )


        except Exception as error:

            print(
                "No se pudo calcular posicion de ID {}: {}".format(
                    element.Id.IntegerValue,
                    error
                )
            )


    return datos


# ============================================================
# ORDEN POR FILAS
#
# SUPERIOR IZQUIERDA -> DERECHA -> CONTINUAR HACIA ABAJO
# ============================================================


def ordenar_elementos_por_filas(elementos):

    datos = _calcular_datos_elementos(elementos)


    # ========================================================
    # ORDEN INICIAL
    # ARRIBA -> ABAJO
    # ========================================================

    datos.sort(
        key=lambda item: -item["y"]
    )


    # ========================================================
    # CREAR FILAS SEGUN SUPERPOSICION VERTICAL
    # ========================================================

    filas = []


    for dato in datos:

        agregado = False


        for fila in filas:


            # ------------------------------------------------
            # COMPROBAR SI EL ELEMENTO SE CRUZA
            # VERTICALMENTE CON LA FILA
            # ------------------------------------------------

            hay_superposicion = (

                dato["y_max"] >= fila["y_min"]
                and
                dato["y_min"] <= fila["y_max"]

            )


            if hay_superposicion:


                fila["elementos"].append(
                    dato
                )


                # --------------------------------------------
                # ACTUALIZAR LOS LIMITES
                # DE LA FILA
                # --------------------------------------------

                fila["y_min"] = min(
                    fila["y_min"],
                    dato["y_min"]
                )


                fila["y_max"] = max(
                    fila["y_max"],
                    dato["y_max"]
                )


                agregado = True

                break


        # ----------------------------------------------------
        # SI NO PERTENECE A NINGUNA FILA
        # CREAMOS UNA NUEVA
        # ----------------------------------------------------

        if not agregado:

            filas.append(
                {
                    "y_min": dato["y_min"],
                    "y_max": dato["y_max"],
                    "elementos": [
                        dato
                    ]
                }
            )


    # ========================================================
    # ORDENAR FILAS
    # DE ARRIBA HACIA ABAJO
    # ========================================================

    filas.sort(

        key=lambda fila: -max(

            item["y"]

            for item in fila["elementos"]

        )

    )


    # ========================================================
    # ORDENAR CADA FILA
    # DE IZQUIERDA A DERECHA
    # ========================================================

    elementos_ordenados = []


    for fila in filas:


        fila["elementos"].sort(
            key=lambda item: item["x"]
        )


        for dato in fila["elementos"]:

            elementos_ordenados.append(
                dato["elemento"]
            )


    _imprimir_orden(elementos_ordenados)


    return elementos_ordenados


# ============================================================
# ORDEN EN CADENA
#
# EMPIEZA EN EL ELEMENTO MAS ARRIBA-IZQUIERDA
# Y SIEMPRE SALTA AL ELEMENTO NO VISITADO MAS CERCANO.
#
# UTIL PARA FRANJAS / PASILLOS / RECORRIDOS QUE SERPENTEAN,
# DONDE EL ORDEN NO SIGUE FILAS RECTAS.
# ============================================================


def ordenar_elementos_en_cadena(elementos, elemento_inicial=None, elemento_final=None):

    datos = _calcular_datos_elementos(elementos)


    if not datos:
        return []


    pendientes = list(datos)


    # ========================================================
    # SI HAY UN ELEMENTO FINAL FIJADO, LO SACAMOS DE LA LISTA
    # DE CANDIDATOS Y LO AGREGAMOS AL FINAL DEL RECORRIDO
    # ========================================================

    dato_final = None


    if elemento_final is not None:

        indice_final = None


        for indice, dato in enumerate(pendientes):

            if dato["elemento"].Id == elemento_final.Id:
                indice_final = indice
                break


        if indice_final is None:

            raise Exception(

                "El elemento final seleccionado no esta "
                "dentro de los elementos a ordenar."

            )


        dato_final = pendientes.pop(indice_final)


    # ========================================================
    # PUNTO DE PARTIDA
    # ========================================================

    if elemento_inicial is not None:

        indice_inicial = None


        for indice, dato in enumerate(pendientes):

            if dato["elemento"].Id == elemento_inicial.Id:
                indice_inicial = indice
                break


        if indice_inicial is None:

            raise Exception(

                "El elemento inicial seleccionado no esta "
                "dentro de los elementos a ordenar."

            )


        actual = pendientes.pop(indice_inicial)


    else:

        # SI NO SE ELIGIO INICIO MANUAL,
        # SE USA EL MAS ARRIBA-IZQUIERDA COMO ANTES

        pendientes.sort(
            key=lambda item: (-item["y"], item["x"])
        )

        actual = pendientes.pop(0)


    elementos_ordenados = [
        actual["elemento"]
    ]


    # ========================================================
    # IR SALTANDO SIEMPRE AL MAS CERCANO
    # (DISTANCIA EUCLIDIANA ENTRE CENTROS PROYECTADOS)
    # ========================================================

    while pendientes:

        mejor_indice = 0
        mejor_distancia = None


        for indice, candidato in enumerate(pendientes):

            dx = candidato["x"] - actual["x"]
            dy = candidato["y"] - actual["y"]

            distancia = (dx * dx) + (dy * dy)


            if mejor_distancia is None or distancia < mejor_distancia:

                mejor_distancia = distancia
                mejor_indice = indice


        actual = pendientes.pop(mejor_indice)

        elementos_ordenados.append(
            actual["elemento"]
        )


    # ========================================================
    # AGREGAR EL ELEMENTO FINAL FIJADO, AL FINAL DEL RECORRIDO
    # ========================================================

    if dato_final is not None:

        elementos_ordenados.append(
            dato_final["elemento"]
        )


    _imprimir_orden(elementos_ordenados)


    return elementos_ordenados


# ============================================================
# IMPRIMIR EL ORDEN CALCULADO EN LA CONSOLA DE PYREVIT
# ============================================================


def _imprimir_orden(elementos_ordenados):

    print(
        "========================================"
    )

    print(
        "ORDEN DE NUMERACION"
    )

    print(
        "========================================"
    )


    contador_debug = 0


    for element in elementos_ordenados:

        print(

            "{} -> ID {}".format(

                str(
                    contador_debug
                ).zfill(
                    2
                ),

                element.Id.IntegerValue

            )

        )


        contador_debug += 1


    print(
        "========================================"
    )


# ============================================================
# ORDEN POR RUTA DIBUJADA
#
# EL USUARIO DIBUJA UNA POLILINEA (CLIC POR CADA PUNTO,
# ENTER PARA TERMINAR). CADA ELEMENTO SE ORDENA SEGUN SU
# POSICION PROYECTADA SOBRE ESA RUTA, DE INICIO A FIN.
# ============================================================


def _proyectar_punto(punto, derecha, arriba):

    x = (
        punto.X * derecha.X
        + punto.Y * derecha.Y
        + punto.Z * derecha.Z
    )

    y = (
        punto.X * arriba.X
        + punto.Y * arriba.Y
        + punto.Z * arriba.Z
    )

    return (x, y)


def _construir_ruta(puntos, derecha, arriba):

    proyectados = [

        _proyectar_punto(punto, derecha, arriba)

        for punto in puntos

    ]


    acumulado = [0.0]


    for indice in range(1, len(proyectados)):

        x0, y0 = proyectados[indice - 1]
        x1, y1 = proyectados[indice]

        distancia = (
            ((x1 - x0) ** 2) + ((y1 - y0) ** 2)
        ) ** 0.5

        acumulado.append(
            acumulado[-1] + distancia
        )


    return proyectados, acumulado


def _distancia_a_lo_largo_de_ruta(punto_xy, ruta_puntos, ruta_acumulado):

    px, py = punto_xy

    mejor_perpendicular = None
    mejor_avance = None


    for indice in range(len(ruta_puntos) - 1):

        x0, y0 = ruta_puntos[indice]
        x1, y1 = ruta_puntos[indice + 1]

        dx = x1 - x0
        dy = y1 - y0

        longitud_cuadrada = (dx * dx) + (dy * dy)


        if longitud_cuadrada == 0:

            parametro_t = 0.0


        else:

            parametro_t = (
                ((px - x0) * dx) + ((py - y0) * dy)
            ) / longitud_cuadrada

            parametro_t = max(
                0.0,
                min(1.0, parametro_t)
            )


        proyeccion_x = x0 + (parametro_t * dx)
        proyeccion_y = y0 + (parametro_t * dy)

        perpendicular = (
            ((px - proyeccion_x) ** 2)
            + ((py - proyeccion_y) ** 2)
        ) ** 0.5

        longitud_segmento = longitud_cuadrada ** 0.5

        avance = (
            ruta_acumulado[indice]
            + (parametro_t * longitud_segmento)
        )


        if mejor_perpendicular is None or perpendicular < mejor_perpendicular:

            mejor_perpendicular = perpendicular
            mejor_avance = avance


    return mejor_avance


def _pedir_puntos_ruta():

    forms.alert(

        "Vas a dibujar la ruta.\n\n"
        "Haz clic en cada punto del recorrido, en orden "
        "(el primer clic sera el 00). Se ira dibujando una "
        "linea guia para que no te pierdas.\n\n"
        "Cuando termines, presiona ESC.",

        title="AAC BIM Selector - Ruta"

    )


    puntos = []

    ids_lineas_temporales = []

    dibujo_fallido = False


    while True:

        try:

            punto = uidoc.Selection.PickPoint(

                "Punto {} de la ruta (ESC para terminar)".format(
                    len(puntos) + 1
                )

            )


        except OperationCanceledException:

            break


        puntos.append(
            punto
        )


        # ----------------------------------------------------
        # DIBUJAR EL TRAMO DESDE EL PUNTO ANTERIOR
        # (SOLO COMO GUIA VISUAL, SE BORRA AL TERMINAR)
        # ----------------------------------------------------

        if len(puntos) >= 2 and not dibujo_fallido:

            transaction_dibujo = Transaction(
                doc,
                "AAC - Tramo de ruta temporal"
            )

            try:

                transaction_dibujo.Start()

                linea = Line.CreateBound(
                    puntos[-2],
                    puntos[-1]
                )

                curva_temporal = doc.Create.NewDetailCurve(
                    doc.ActiveView,
                    linea
                )

                ids_lineas_temporales.append(
                    curva_temporal.Id
                )

                transaction_dibujo.Commit()


            except Exception as error:

                if transaction_dibujo.HasStarted() and not transaction_dibujo.HasEnded():
                    transaction_dibujo.RollBack()

                dibujo_fallido = True

                forms.alert(

                    "No se pudo dibujar la linea guia:\n\n"
                    "{}\n\n"
                    "Puedes seguir marcando los puntos, pero sin "
                    "guia visual. Revisa que:\n\n"
                    "- La vista activa sea planta, seccion, alzado "
                    "o vista de detalle (no 3D)\n"
                    "- La categoria 'Lineas' este visible en "
                    "Visibilidad/Grafismo (VV)\n"
                    "- El subproyecto activo este visible en "
                    "esta vista\n"
                    "- No haya un Aislar/Ocultar temporal activo".format(
                        error
                    ),

                    title="AAC BIM Selector - Aviso"

                )


    # ========================================================
    # BORRAR LA RUTA TEMPORAL (SOLO ERA UNA GUIA VISUAL)
    # ========================================================

    if ids_lineas_temporales:

        transaction_borrado = Transaction(
            doc,
            "AAC - Borrar ruta temporal"
        )

        try:

            transaction_borrado.Start()

            for id_linea in ids_lineas_temporales:
                doc.Delete(id_linea)

            transaction_borrado.Commit()


        except Exception as error:

            if transaction_borrado.HasStarted() and not transaction_borrado.HasEnded():
                transaction_borrado.RollBack()

            print(
                "No se pudieron borrar las lineas guia: {}".format(
                    error
                )
            )


    return puntos


def ordenar_elementos_por_ruta(elementos):

    vista = doc.ActiveView

    derecha = vista.RightDirection
    arriba = vista.UpDirection


    puntos = _pedir_puntos_ruta()


    if not puntos or len(puntos) < 2:

        raise Exception(

            "Debes dibujar al menos 2 puntos para definir la ruta."

        )


    ruta_puntos, ruta_acumulado = _construir_ruta(
        puntos, derecha, arriba
    )


    datos = _calcular_datos_elementos(elementos)


    for dato in datos:

        dato["avance"] = _distancia_a_lo_largo_de_ruta(
            (dato["x"], dato["y"]),
            ruta_puntos,
            ruta_acumulado
        )


    datos.sort(
        key=lambda item: item["avance"]
    )


    elementos_ordenados = [
        dato["elemento"] for dato in datos
    ]


    _imprimir_orden(elementos_ordenados)


    return elementos_ordenados


# ============================================================
# FUNCION PARA NOMBRAR
# ============================================================


def nombrar_elementos(elementos):


    if not elementos:

        forms.alert(
            "No hay elementos para nombrar.",
            title="AAC BIM Selector"
        )

        return


    # ========================================================
    # PARAMETROS DISPONIBLES
    # ========================================================

    parametros_disponibles = obtener_parametros_texto_comunes(
        elementos
    )


    if not parametros_disponibles:

        forms.alert(

            "No se encontraron parametros de texto editables "
            "comunes a todos los elementos.",

            title="AAC BIM Selector"

        )

        return


    # ========================================================
    # SELECCIONAR PARAMETRO
    # ========================================================

    parametro_seleccionado = forms.SelectFromList.show(

        parametros_disponibles,

        title="AAC BIM Selector - Parametro",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not parametro_seleccionado:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # PREFIJO
    # ========================================================

    prefijo = forms.ask_for_string(

        default="",

        prompt="Escribe el prefijo:",

        title="AAC BIM Selector - Prefijo"

    )


    if prefijo is None:

        raise Exception(
            "Operacion cancelada."
        )


    prefijo = prefijo.strip()


    # ========================================================
    # NUMERO INICIAL
    # ========================================================

    numero_inicial_texto = forms.ask_for_string(

        default="00",

        prompt="Escribe el numero inicial:",

        title="AAC BIM Selector - Numeracion"

    )


    if numero_inicial_texto is None:

        raise Exception(
            "Operacion cancelada."
        )


    try:

        numero_inicial = int(
            numero_inicial_texto
        )


    except:

        raise Exception(
            "El numero inicial debe ser un numero entero."
        )


    # ========================================================
    # MODO DE ORDEN
    # ========================================================

    modo_orden = forms.CommandSwitchWindow.show(

        [
            "Filas (arriba-abajo, izquierda-derecha)",
            "Cadena (siempre el mas cercano)",
            "Ruta dibujada (tu marcas el camino)"
        ],

        message="¿Como quieres ordenar los elementos?"

    )


    if not modo_orden:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # ORDENAR SEGUN POSICION EN LA VISTA
    # ========================================================

    if modo_orden == "Cadena (siempre el mas cercano)":

        elemento_inicial = None
        elemento_final = None


        definir_extremos = forms.alert(

            "¿Quieres elegir manualmente cual es el PRIMER "
            "elemento (sera el numero inicial) y cual el ULTIMO "
            "de la cadena?",

            title="AAC BIM Selector - Cadena",

            yes=True,

            no=True

        )


        if definir_extremos:

            referencia_inicio = uidoc.Selection.PickObject(

                ObjectType.Element,

                "Selecciona el PRIMER elemento de la cadena"

            )

            elemento_inicial = doc.GetElement(
                referencia_inicio.ElementId
            )


            referencia_final = uidoc.Selection.PickObject(

                ObjectType.Element,

                "Selecciona el ULTIMO elemento de la cadena"

            )

            elemento_final = doc.GetElement(
                referencia_final.ElementId
            )


            if elemento_inicial.Id == elemento_final.Id:

                raise Exception(

                    "El primer y ultimo elemento no pueden "
                    "ser el mismo."

                )


        elementos_ordenados = ordenar_elementos_en_cadena(
            elementos,
            elemento_inicial,
            elemento_final
        )

    elif modo_orden == "Ruta dibujada (tu marcas el camino)":

        elementos_ordenados = ordenar_elementos_por_ruta(
            elementos
        )

    else:

        elementos_ordenados = ordenar_elementos_por_filas(
            elementos
        )


    if not elementos_ordenados:

        raise Exception(
            "No se pudo calcular la posicion de los elementos."
        )


    # ========================================================
    # CANTIDAD MINIMA DE DIGITOS
    #
    # Cada numero usa AL MENOS esta cantidad de digitos
    # (ej: 2 -> 00, 01 ... 99, 100, 101 ...).
    # Los numeros de una cifra mayor crecen solos, sin
    # afectar el formato de los numeros anteriores.
    # ========================================================

    digitos_texto = forms.ask_for_string(

        default="2",

        prompt="¿Minimo de digitos? (ej: 2 -> 00, 01... 99, 100, 101...)",

        title="AAC BIM Selector - Digitos"

    )


    if digitos_texto is None:

        raise Exception(
            "Operacion cancelada."
        )


    try:

        digitos = int(digitos_texto)

    except:

        raise Exception(
            "La cantidad de digitos debe ser un numero entero."
        )


    # ========================================================
    # VISTA PREVIA
    # ========================================================

    vista_previa = ""

    contador = numero_inicial


    for element in elementos_ordenados[:15]:


        numero_formateado = str(
            contador
        ).zfill(
            digitos
        )


        if prefijo:

            nombre_nuevo = "{}-{}".format(
                prefijo,
                numero_formateado
            )


        else:

            nombre_nuevo = numero_formateado


        vista_previa += (

            "{}    ID {}\n".format(

                nombre_nuevo,

                element.Id.IntegerValue

            )

        )


        contador += 1


    if len(elementos_ordenados) > 15:

        vista_previa += "\n..."


    # ========================================================
    # CONFIRMAR
    # ========================================================

    mensaje = (

        "Se van a modificar {} elementos.\n\n"

        "Parametro: {}\n"

        "Prefijo: {}\n"

        "Numero inicial: {}\n\n"

        "Orden:\n"

        "Superior izquierda -> derecha -> abajo\n\n"

        "Vista previa:\n\n{}"

    ).format(

        len(elementos_ordenados),

        parametro_seleccionado,

        prefijo if prefijo else "(sin prefijo)",

        numero_inicial,

        vista_previa

    )


    confirmar = forms.alert(

        mensaje,

        title="AAC BIM Selector - Confirmar nombres",

        yes=True,

        no=True

    )


    if not confirmar:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # TRANSACTION
    # ========================================================

    transaction = Transaction(
        doc,
        "AAC - Nombrar elementos"
    )


    transaction.Start()


    contador = numero_inicial

    modificados = 0

    errores = []


    try:


        for element in elementos_ordenados:


            numero_formateado = str(
                contador
            ).zfill(
                digitos
            )


            if prefijo:

                nombre_nuevo = "{}-{}".format(
                    prefijo,
                    numero_formateado
                )


            else:

                nombre_nuevo = numero_formateado


            parametro = element.LookupParameter(
                parametro_seleccionado
            )


            if not parametro:

                errores.append(

                    "ID {} - parametro no encontrado".format(
                        element.Id.IntegerValue
                    )

                )

                contador += 1

                continue


            if parametro.IsReadOnly:

                errores.append(

                    "ID {} - parametro de solo lectura".format(
                        element.Id.IntegerValue
                    )

                )

                contador += 1

                continue


            if parametro.StorageType != StorageType.String:

                errores.append(

                    "ID {} - parametro no es texto".format(
                        element.Id.IntegerValue
                    )

                )

                contador += 1

                continue


            parametro.Set(
                nombre_nuevo
            )


            modificados += 1

            contador += 1


        transaction.Commit()


    except Exception as error:

        transaction.RollBack()

        raise error


    # ========================================================
    # RESULTADO
    # ========================================================

    mensaje_resultado = (

        "{} elementos nombrados correctamente."

    ).format(
        modificados
    )


    if errores:

        mensaje_resultado += (

            "\n\n{} elementos no pudieron modificarse."

        ).format(
            len(errores)
        )


    forms.alert(

        mensaje_resultado,

        title="AAC BIM Selector"

    )


# ============================================================
# FUNCION PARA NOMBRAR PLATAFORMAS SEGUN EL SUELO
#
# CADA PLATAFORMA HEREDA EL NOMBRE DEL SUELO QUE TIENE ENCIMA
# (POR SOLAPE EN PLANTA), MAS UNA LETRA SEGUN SU POSICION
# DENTRO DE ESE SUELO: P-00-A, P-00-B, P-00-C ...
# ============================================================


# ============================================================
# UTILIDADES DE SUBPROYECTO (REUTILIZABLES)
# ============================================================


def _listar_subproyectos(elementos):

    workset_table = doc.GetWorksetTable()

    nombres = []


    for element in elementos:

        try:

            workset = workset_table.GetWorkset(
                element.WorksetId
            )

            if workset and workset.Name not in nombres:
                nombres.append(workset.Name)

        except:
            pass


    nombres.sort()

    nombres.insert(0, "<Todos>")

    return nombres


def _filtrar_por_subproyecto(elementos, nombre_subproyecto):

    if nombre_subproyecto == "<Todos>":
        return elementos


    workset_table = doc.GetWorksetTable()

    resultado = []


    for element in elementos:

        try:

            workset = workset_table.GetWorkset(
                element.WorksetId
            )

            if workset and workset.Name == nombre_subproyecto:
                resultado.append(element)

        except:
            pass


    return resultado


def nombrar_plataformas_segun_suelo():


    # ========================================================
    # TODAS LAS CATEGORIAS DEL MODELO
    # ========================================================

    collector = FilteredElementCollector(doc)\
        .WhereElementIsNotElementType()

    todos_los_elementos = list(collector)


    categorias_disponibles = []


    for element in todos_los_elementos:

        try:

            categoria = element.Category

            if categoria and categoria.Name:

                if categoria.Name not in categorias_disponibles:
                    categorias_disponibles.append(categoria.Name)

        except:
            pass


    categorias_disponibles.sort()


    # ========================================================
    # CATEGORIA DE SUELOS (YA NOMBRADOS)
    # ========================================================

    categoria_suelo = forms.SelectFromList.show(

        categorias_disponibles,

        title="AAC BIM Selector - Categoria de SUELOS (ya nombrados)",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not categoria_suelo:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # CATEGORIA DE PLATAFORMAS A NOMBRAR
    # ========================================================

    categoria_plataforma = forms.SelectFromList.show(

        categorias_disponibles,

        title="AAC BIM Selector - Categoria de PLATAFORMAS a nombrar",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not categoria_plataforma:

        raise Exception(
            "Operacion cancelada."
        )


    if categoria_plataforma == categoria_suelo:

        raise Exception(

            "La categoria de plataformas debe ser distinta "
            "a la de suelos."

        )


    # ========================================================
    # RECOPILAR ELEMENTOS DE CADA CATEGORIA
    # ========================================================

    suelos = []

    plataformas = []


    for element in todos_los_elementos:

        try:

            if not element.Category:
                continue

            if element.Category.Name == categoria_suelo:
                suelos.append(element)

            elif element.Category.Name == categoria_plataforma:
                plataformas.append(element)

        except:
            pass


    if not suelos:

        raise Exception(

            "No se encontraron elementos de la categoria "
            "'{}'.".format(categoria_suelo)

        )


    if not plataformas:

        raise Exception(

            "No se encontraron elementos de la categoria "
            "'{}'.".format(categoria_plataforma)

        )


    # ========================================================
    # FILTRAR POR SUBPROYECTO
    # (SUELOS Y PLATAFORMAS PUEDEN VIVIR EN SUBPROYECTOS
    # DISTINTOS, EJ: P-JARDIN Y PLT-JARDIN)
    # ========================================================

    # --------------------------------------------------------
    # SUBPROYECTO DE SUELOS
    # --------------------------------------------------------

    subproyecto_suelo = forms.SelectFromList.show(

        _listar_subproyectos(suelos),

        title="AAC BIM Selector - Subproyecto de SUELOS",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not subproyecto_suelo:

        raise Exception(
            "Operacion cancelada."
        )


    suelos = _filtrar_por_subproyecto(
        suelos, subproyecto_suelo
    )


    if not suelos:

        raise Exception(

            "No hay suelos de la categoria '{}' en el "
            "subproyecto '{}'.".format(
                categoria_suelo,
                subproyecto_suelo
            )

        )


    # --------------------------------------------------------
    # SUBPROYECTO DE PLATAFORMAS
    # --------------------------------------------------------

    subproyecto_plataforma = forms.SelectFromList.show(

        _listar_subproyectos(plataformas),

        title="AAC BIM Selector - Subproyecto de PLATAFORMAS",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not subproyecto_plataforma:

        raise Exception(
            "Operacion cancelada."
        )


    plataformas = _filtrar_por_subproyecto(
        plataformas, subproyecto_plataforma
    )


    if not plataformas:

        raise Exception(

            "No hay plataformas de la categoria '{}' en el "
            "subproyecto '{}'.".format(
                categoria_plataforma,
                subproyecto_plataforma
            )

        )


    # ========================================================
    # PARAMETRO DONDE YA ESTA EL NOMBRE DE LOS SUELOS
    # ========================================================

    parametros_suelo = obtener_parametros_texto_comunes(suelos)


    if not parametros_suelo:

        raise Exception(

            "No se encontro un parametro de texto comun en "
            "los suelos."

        )


    parametro_suelo = forms.SelectFromList.show(

        parametros_suelo,

        title="AAC BIM Selector - Parametro con el nombre del SUELO",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not parametro_suelo:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # PARAMETRO DONDE SE VA A ESCRIBIR EL NOMBRE
    # DE LAS PLATAFORMAS
    # ========================================================

    parametros_plataforma = obtener_parametros_texto_comunes(
        plataformas
    )


    if not parametros_plataforma:

        raise Exception(

            "No se encontro un parametro de texto comun en "
            "las plataformas."

        )


    parametro_plataforma = forms.SelectFromList.show(

        parametros_plataforma,

        title="AAC BIM Selector - Parametro para nombrar PLATAFORMAS",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not parametro_plataforma:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # LEER EL NOMBRE ACTUAL DE CADA SUELO
    # ========================================================

    suelos_con_nombre = []

    cantidad_suelos_sin_nombre = 0


    for suelo in suelos:

        parametro = suelo.LookupParameter(
            parametro_suelo
        )

        valor = parametro.AsString() if parametro else None


        if valor and valor.strip():

            suelos_con_nombre.append(
                (suelo, valor.strip())
            )


        else:

            cantidad_suelos_sin_nombre += 1


    if not suelos_con_nombre:

        raise Exception(

            "Ningun suelo tiene nombre asignado en el "
            "parametro '{}'. Nombra los suelos primero.".format(
                parametro_suelo
            )

        )


    if cantidad_suelos_sin_nombre:

        forms.alert(

            "{} suelo(s) no tienen nombre asignado en '{}' "
            "y se ignoraran (sus plataformas no podran "
            "vincularse a ellos).".format(

                cantidad_suelos_sin_nombre,
                parametro_suelo

            ),

            title="AAC BIM Selector - Aviso"

        )


    # ========================================================
    # ASIGNAR CADA PLATAFORMA AL SUELO CON MAYOR SOLAPE
    # ========================================================

    UMBRAL_CONTENCION = 0.5


    datos_suelo = []


    for suelo, nombre in suelos_con_nombre:

        bbox = obtener_bbox_mundial(suelo)

        if bbox:

            datos_suelo.append(
                (suelo, nombre, bbox)
            )


    grupos_por_suelo = {}

    plataformas_sin_suelo = []


    for plataforma in plataformas:

        bbox_plataforma = obtener_bbox_mundial(plataforma)


        if not bbox_plataforma:

            plataformas_sin_suelo.append(
                (plataforma, None, 0.0)
            )
            continue


        mejor_nombre = None

        mejor_ratio = 0.0


        for suelo, nombre, bbox_suelo in datos_suelo:

            ratio = calcular_solape_xy(
                bbox_plataforma,
                bbox_suelo
            )

            if ratio > mejor_ratio:

                mejor_ratio = ratio
                mejor_nombre = nombre


        if mejor_nombre is not None and mejor_ratio >= UMBRAL_CONTENCION:

            if mejor_nombre not in grupos_por_suelo:
                grupos_por_suelo[mejor_nombre] = []

            grupos_por_suelo[mejor_nombre].append(
                plataforma
            )


        else:

            plataformas_sin_suelo.append(
                (plataforma, mejor_nombre, mejor_ratio)
            )


    if not grupos_por_suelo:

        raise Exception(

            "No se pudo vincular ninguna plataforma con un "
            "suelo. Revisa que se solapen en planta."

        )


    # ========================================================
    # MODO DE ORDEN DENTRO DE CADA SUELO
    # ========================================================

    modo_orden = forms.CommandSwitchWindow.show(

        [
            "Filas (arriba-abajo, izquierda-derecha)",
            "Cadena (siempre el mas cercano)"
        ],

        message="¿Como ordenar las plataformas DENTRO de cada suelo?"

    )


    if not modo_orden:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # ARMAR LAS ASIGNACIONES: PLATAFORMA -> NOMBRE NUEVO
    # ========================================================

    asignaciones = []


    for nombre_suelo in sorted(grupos_por_suelo.keys()):

        plataformas_grupo = grupos_por_suelo[nombre_suelo]


        if modo_orden == "Cadena (siempre el mas cercano)":

            plataformas_ordenadas = ordenar_elementos_en_cadena(
                plataformas_grupo
            )


        else:

            plataformas_ordenadas = ordenar_elementos_por_filas(
                plataformas_grupo
            )


        for indice, plataforma in enumerate(plataformas_ordenadas):

            letra = _letra_desde_indice(indice)

            nombre_nuevo = "{}-{}".format(
                nombre_suelo,
                letra
            )

            asignaciones.append(
                (plataforma, nombre_nuevo)
            )


    # ========================================================
    # VISTA PREVIA
    # ========================================================

    vista_previa = ""


    for plataforma, nombre_nuevo in asignaciones[:20]:

        vista_previa += (
            "{}    ID {}\n".format(
                nombre_nuevo,
                plataforma.Id.IntegerValue
            )
        )


    if len(asignaciones) > 20:
        vista_previa += "\n..."


    mensaje = (

        "Se van a nombrar {} plataformas, agrupadas bajo "
        "{} suelos.\n\n"
        "Parametro suelo (lectura): {}\n"
        "Parametro plataforma (escritura): {}\n\n"

    ).format(

        len(asignaciones),
        len(grupos_por_suelo),
        parametro_suelo,
        parametro_plataforma

    )


    if plataformas_sin_suelo:

        mensaje += (

            "ATENCION: {} plataforma(s) no se pudieron "
            "vincular a ningun suelo y se ignoraran.\n\n"

        ).format(len(plataformas_sin_suelo))


    mensaje += "Vista previa:\n\n{}".format(vista_previa)


    confirmar = forms.alert(

        mensaje,

        title="AAC BIM Selector - Confirmar",

        yes=True,

        no=True

    )


    if not confirmar:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # TRANSACTION
    # ========================================================

    transaction = Transaction(
        doc,
        "AAC - Nombrar plataformas segun suelo"
    )


    transaction.Start()


    modificados = 0

    errores = []


    try:


        for plataforma, nombre_nuevo in asignaciones:


            parametro = plataforma.LookupParameter(
                parametro_plataforma
            )


            if not parametro:

                errores.append(
                    "ID {} - parametro no encontrado".format(
                        plataforma.Id.IntegerValue
                    )
                )

                continue


            if parametro.IsReadOnly:

                errores.append(
                    "ID {} - parametro de solo lectura".format(
                        plataforma.Id.IntegerValue
                    )
                )

                continue


            if parametro.StorageType != StorageType.String:

                errores.append(
                    "ID {} - parametro no es texto".format(
                        plataforma.Id.IntegerValue
                    )
                )

                continue


            parametro.Set(
                nombre_nuevo
            )

            modificados += 1


        transaction.Commit()


    except Exception as error:

        transaction.RollBack()

        raise error


    # ========================================================
    # RESULTADO
    # ========================================================

    mensaje_resultado = (
        "{} plataformas nombradas correctamente."
    ).format(modificados)


    if plataformas_sin_suelo:

        mensaje_resultado += (
            "\n\n{} plataformas no se pudieron vincular a "
            "un suelo (quedaron seleccionadas en el modelo "
            "para que las revises):\n"
        ).format(len(plataformas_sin_suelo))


        for plataforma, mejor_nombre, mejor_ratio in plataformas_sin_suelo[:15]:

            if mejor_nombre is not None:

                mensaje_resultado += (
                    "\n  ID {} -> mas cercano: '{}' "
                    "({:.0f}% de solape, se necesita 50%)".format(
                        plataforma.Id.IntegerValue,
                        mejor_nombre,
                        mejor_ratio * 100
                    )
                )

            else:

                mensaje_resultado += (
                    "\n  ID {} -> no se solapa con ningun "
                    "suelo nombrado".format(
                        plataforma.Id.IntegerValue
                    )
                )


        if len(plataformas_sin_suelo) > 15:
            mensaje_resultado += "\n  ..."


        # ----------------------------------------------------
        # SELECCIONAR Y FORZAR ZOOM A LAS PLATAFORMAS
        # SIN VINCULAR
        # ----------------------------------------------------

        _enfocar_elementos(
            [item[0] for item in plataformas_sin_suelo]
        )


    if errores:

        mensaje_resultado += (
            "\n\n{} plataformas no pudieron modificarse."
        ).format(len(errores))


    forms.alert(

        mensaje_resultado,

        title="AAC BIM Selector"

    )


# ============================================================
# FUNCION PARA NOMBRAR TOPOGRAFIA / SUBREGION
# SEGUN LA PLATAFORMA
#
# CADA TOPOGRAFIA/SUBREGION HEREDA EXACTAMENTE EL MISMO
# NOMBRE DE LA PLATAFORMA QUE TIENE DEBAJO (POR SOLAPE EN
# PLANTA). ES UNA RELACION 1 A 1, SIN LETRA.
# ============================================================


def nombrar_topografia_segun_plataforma():


    # ========================================================
    # TODAS LAS CATEGORIAS DEL MODELO
    # ========================================================

    collector = FilteredElementCollector(doc)\
        .WhereElementIsNotElementType()

    todos_los_elementos = list(collector)


    categorias_disponibles = []


    for element in todos_los_elementos:

        try:

            categoria = element.Category

            if categoria and categoria.Name:

                if categoria.Name not in categorias_disponibles:
                    categorias_disponibles.append(categoria.Name)

        except:
            pass


    categorias_disponibles.sort()


    # ========================================================
    # CATEGORIA DE PLATAFORMAS (YA NOMBRADAS)
    # ========================================================

    categoria_plataforma = forms.SelectFromList.show(

        categorias_disponibles,

        title="AAC BIM Selector - Categoria de PLATAFORMAS (ya nombradas)",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not categoria_plataforma:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # CATEGORIA DE TOPOGRAFIA / SUBREGION A NOMBRAR
    # ========================================================

    categoria_topografia = forms.SelectFromList.show(

        categorias_disponibles,

        title="AAC BIM Selector - Categoria de TOPOGRAFIA/SUBREGION a nombrar",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not categoria_topografia:

        raise Exception(
            "Operacion cancelada."
        )


    if categoria_topografia == categoria_plataforma:

        raise Exception(

            "La categoria de topografia/subregion debe ser "
            "distinta a la de plataformas."

        )


    # ========================================================
    # RECOPILAR ELEMENTOS DE CADA CATEGORIA
    # ========================================================

    plataformas = []

    topografias = []


    for element in todos_los_elementos:

        try:

            if not element.Category:
                continue

            if element.Category.Name == categoria_plataforma:
                plataformas.append(element)

            elif element.Category.Name == categoria_topografia:
                topografias.append(element)

        except:
            pass


    if not plataformas:

        raise Exception(

            "No se encontraron elementos de la categoria "
            "'{}'.".format(categoria_plataforma)

        )


    if not topografias:

        raise Exception(

            "No se encontraron elementos de la categoria "
            "'{}'.".format(categoria_topografia)

        )


    # ========================================================
    # FILTRAR POR SUBPROYECTO
    # (PLATAFORMAS Y TOPOGRAFIA PUEDEN VIVIR EN SUBPROYECTOS
    # DISTINTOS)
    # ========================================================

    subproyecto_plataforma = forms.SelectFromList.show(

        _listar_subproyectos(plataformas),

        title="AAC BIM Selector - Subproyecto de PLATAFORMAS",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not subproyecto_plataforma:

        raise Exception(
            "Operacion cancelada."
        )


    plataformas = _filtrar_por_subproyecto(
        plataformas, subproyecto_plataforma
    )


    if not plataformas:

        raise Exception(

            "No hay plataformas de la categoria '{}' en el "
            "subproyecto '{}'.".format(
                categoria_plataforma,
                subproyecto_plataforma
            )

        )


    subproyecto_topografia = forms.SelectFromList.show(

        _listar_subproyectos(topografias),

        title="AAC BIM Selector - Subproyecto de TOPOGRAFIA/SUBREGION",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not subproyecto_topografia:

        raise Exception(
            "Operacion cancelada."
        )


    topografias = _filtrar_por_subproyecto(
        topografias, subproyecto_topografia
    )


    if not topografias:

        raise Exception(

            "No hay elementos de la categoria '{}' en el "
            "subproyecto '{}'.".format(
                categoria_topografia,
                subproyecto_topografia
            )

        )


    # ========================================================
    # PARAMETRO DONDE YA ESTA EL NOMBRE DE LAS PLATAFORMAS
    # ========================================================

    parametros_plataforma = obtener_parametros_texto_comunes(
        plataformas
    )


    if not parametros_plataforma:

        raise Exception(

            "No se encontro un parametro de texto comun en "
            "las plataformas."

        )


    parametro_plataforma = forms.SelectFromList.show(

        parametros_plataforma,

        title="AAC BIM Selector - Parametro con el nombre de la PLATAFORMA",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not parametro_plataforma:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # PARAMETRO DONDE SE VA A ESCRIBIR EL NOMBRE
    # DE LA TOPOGRAFIA/SUBREGION
    # ========================================================

    parametros_topografia = obtener_parametros_texto_comunes(
        topografias
    )


    if not parametros_topografia:

        raise Exception(

            "No se encontro un parametro de texto comun en "
            "la topografia/subregion."

        )


    parametro_topografia = forms.SelectFromList.show(

        parametros_topografia,

        title="AAC BIM Selector - Parametro para nombrar TOPOGRAFIA/SUBREGION",

        button_name="Siguiente",

        multiselect=False,

        width=500

    )


    if not parametro_topografia:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # LEER EL NOMBRE ACTUAL DE CADA PLATAFORMA
    # ========================================================

    plataformas_con_nombre = []

    cantidad_plataformas_sin_nombre = 0


    for plataforma in plataformas:

        parametro = plataforma.LookupParameter(
            parametro_plataforma
        )

        valor = parametro.AsString() if parametro else None


        if valor and valor.strip():

            plataformas_con_nombre.append(
                (plataforma, valor.strip())
            )


        else:

            cantidad_plataformas_sin_nombre += 1


    if not plataformas_con_nombre:

        raise Exception(

            "Ninguna plataforma tiene nombre asignado en el "
            "parametro '{}'. Nombra las plataformas primero.".format(
                parametro_plataforma
            )

        )


    if cantidad_plataformas_sin_nombre:

        forms.alert(

            "{} plataforma(s) no tienen nombre asignado en "
            "'{}' y se ignoraran.".format(

                cantidad_plataformas_sin_nombre,
                parametro_plataforma

            ),

            title="AAC BIM Selector - Aviso"

        )


    # ========================================================
    # ASIGNAR CADA TOPOGRAFIA/SUBREGION A LA PLATAFORMA
    # CON MAYOR SOLAPE (RELACION 1 A 1)
    # ========================================================

    UMBRAL_CONTENCION = 0.5


    datos_plataforma = []


    for plataforma, nombre in plataformas_con_nombre:

        bbox = obtener_bbox_mundial(plataforma)

        if bbox:

            datos_plataforma.append(
                (plataforma, nombre, bbox)
            )


    asignaciones = []

    topografias_sin_plataforma = []


    for topografia in topografias:

        bbox_topografia = obtener_bbox_mundial(topografia)


        if not bbox_topografia:

            topografias_sin_plataforma.append(
                (topografia, None, 0.0)
            )
            continue


        mejor_nombre = None

        mejor_ratio = 0.0


        for plataforma, nombre, bbox_plataforma in datos_plataforma:

            ratio = calcular_solape_xy(
                bbox_topografia,
                bbox_plataforma
            )

            if ratio > mejor_ratio:

                mejor_ratio = ratio
                mejor_nombre = nombre


        if mejor_nombre is not None and mejor_ratio >= UMBRAL_CONTENCION:

            asignaciones.append(
                (topografia, mejor_nombre)
            )


        else:

            topografias_sin_plataforma.append(
                (topografia, mejor_nombre, mejor_ratio)
            )


    if not asignaciones:

        raise Exception(

            "No se pudo vincular ninguna topografia/subregion "
            "con una plataforma. Revisa que se solapen en planta."

        )


    # ========================================================
    # VISTA PREVIA
    # ========================================================

    vista_previa = ""


    for topografia, nombre_nuevo in asignaciones[:20]:

        vista_previa += (
            "{}    ID {}\n".format(
                nombre_nuevo,
                topografia.Id.IntegerValue
            )
        )


    if len(asignaciones) > 20:
        vista_previa += "\n..."


    mensaje = (

        "Se van a nombrar {} elementos de topografia/subregion, "
        "segun su plataforma correspondiente.\n\n"
        "Parametro plataforma (lectura): {}\n"
        "Parametro topografia (escritura): {}\n\n"

    ).format(

        len(asignaciones),
        parametro_plataforma,
        parametro_topografia

    )


    if topografias_sin_plataforma:

        mensaje += (

            "ATENCION: {} elemento(s) de topografia/subregion "
            "no se pudieron vincular a ninguna plataforma y se "
            "ignoraran.\n\n"

        ).format(len(topografias_sin_plataforma))


    mensaje += "Vista previa:\n\n{}".format(vista_previa)


    confirmar = forms.alert(

        mensaje,

        title="AAC BIM Selector - Confirmar",

        yes=True,

        no=True

    )


    if not confirmar:

        raise Exception(
            "Operacion cancelada."
        )


    # ========================================================
    # TRANSACTION
    # ========================================================

    transaction = Transaction(
        doc,
        "AAC - Nombrar topografia segun plataforma"
    )


    transaction.Start()


    modificados = 0

    errores = []


    try:


        for topografia, nombre_nuevo in asignaciones:


            parametro = topografia.LookupParameter(
                parametro_topografia
            )


            if not parametro:

                errores.append(
                    "ID {} - parametro no encontrado".format(
                        topografia.Id.IntegerValue
                    )
                )

                continue


            if parametro.IsReadOnly:

                errores.append(
                    "ID {} - parametro de solo lectura".format(
                        topografia.Id.IntegerValue
                    )
                )

                continue


            if parametro.StorageType != StorageType.String:

                errores.append(
                    "ID {} - parametro no es texto".format(
                        topografia.Id.IntegerValue
                    )
                )

                continue


            parametro.Set(
                nombre_nuevo
            )

            modificados += 1


        transaction.Commit()


    except Exception as error:

        transaction.RollBack()

        raise error


    # ========================================================
    # RESULTADO
    # ========================================================

    mensaje_resultado = (
        "{} elementos de topografia/subregion nombrados "
        "correctamente."
    ).format(modificados)


    if topografias_sin_plataforma:

        mensaje_resultado += (
            "\n\n{} elementos no se pudieron vincular a "
            "una plataforma (quedaron seleccionados en el "
            "modelo para que los revises):\n"
        ).format(len(topografias_sin_plataforma))


        for topografia, mejor_nombre, mejor_ratio in topografias_sin_plataforma[:15]:

            if mejor_nombre is not None:

                mensaje_resultado += (
                    "\n  ID {} -> mas cercano: '{}' "
                    "({:.0f}% de solape, se necesita 50%)".format(
                        topografia.Id.IntegerValue,
                        mejor_nombre,
                        mejor_ratio * 100
                    )
                )

            else:

                mensaje_resultado += (
                    "\n  ID {} -> no se solapa con ninguna "
                    "plataforma nombrada".format(
                        topografia.Id.IntegerValue
                    )
                )


        if len(topografias_sin_plataforma) > 15:
            mensaje_resultado += "\n  ..."


        # ----------------------------------------------------
        # SELECCIONAR Y FORZAR ZOOM A LAS TOPOGRAFIAS/
        # SUBREGIONES SIN VINCULAR
        # ----------------------------------------------------

        _enfocar_elementos(
            [item[0] for item in topografias_sin_plataforma]
        )


    if errores:

        mensaje_resultado += (
            "\n\n{} elementos no pudieron modificarse."
        ).format(len(errores))


    forms.alert(

        mensaje_resultado,

        title="AAC BIM Selector"

    )


