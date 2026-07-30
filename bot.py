import pandas as pd
import csv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from zoneinfo import ZoneInfo
from datetime import datetime, time
import nest_asyncio
import os

nest_asyncio.apply()

# =========================
# CONFIG
# =========================

TOKEN = "7119344534:AAFJP-0BM9OvIoo_bw2RDB5nfm0HVGBKKxQ"
CHAT_ID = 5504611412
CSV_FILE = "/data/clientes.csv"

# =========================
# ESTADOS DE CONVERSACIÓN
# =========================

(
    NOMBRE,
    SERVICIO,
    CUENTA,
    DIAS,
    FECHA,
    CONFIRMAR,

    MOD_NOMBRE,
    MOD_FACTURA,
    MOD_ACCION,
    MOD_DIAS,
    MOD_CUENTA,
    MOD_FECHA,
    MOD_SERVICIO,
    MOD_CLIENTE

) = range(14)
# Datos temporales de la conversación
datos_cliente = {}

# =========================
# CREAR CSV SI NO EXISTE
# =========================

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        writer.writerow([
            "Factura",
            "Cliente",
            "Fecha_Emision",
            "Dias",
            "Servicio",
            "Cuenta"
        ])

# =========================
# LEER DATOS
# =========================

def leer_datos():

    df = pd.read_csv(CSV_FILE)

    if df.empty:
        return df

    # Limpiar columnas
    df.columns = [str(col).strip() for col in df.columns]

    # Convertir fecha
    df["Fecha_Emision"] = pd.to_datetime(
        df["Fecha_Emision"],
        errors="coerce"
    )

    # Convertir días
    df["Dias"] = pd.to_numeric(
        df["Dias"],
        errors="coerce"
    )

    # Calcular vencimiento
    df["Fecha_Vencimiento"] = (
        df["Fecha_Emision"] +
        pd.to_timedelta(df["Dias"], unit="D")
    )

    hoy = pd.Timestamp.now().normalize()

    # Calcular días restantes
    df["Dias_Restantes"] = (
        df["Fecha_Vencimiento"] - hoy
    ).dt.days

    # Crear alertas
    def generar_alerta(dias):

        if pd.isna(dias):
            return "SIN FECHA"

        if dias < 0:
            return f"❌ VENCIDO hace {abs(dias)} días"

        elif dias <= 3:
            return f"⚠️ FALTAN {dias} días"

        else:
            return f"✅ Faltan {dias} días"

    df["Alerta"] = df["Dias_Restantes"].apply(generar_alerta)

    return df

# =========================
# GENERAR FACTURA
# =========================

def generar_factura():

    df = leer_datos()

    if df.empty:
        return "Fact_001"

    numeros = []

    for factura in df["Factura"]:

        try:
            numero = int(str(factura).replace("Fact_", ""))
            numeros.append(numero)

        except:
            pass

    if not numeros:
        return "Fact_001"

    nuevo = max(numeros) + 1

    return f"Fact_{str(nuevo).zfill(3)}"


# =========================
# GUARDAR CSV
# =========================

def guardar_cliente(
    factura,
    nombre,
    fecha,
    dias,
    servicio,
    cuenta
):

    with open(
        CSV_FILE,
        mode="a",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            factura,
            nombre,
            fecha,
            dias,
            servicio,
            cuenta
        ])
# =========================
# OBTENER CHAT ID
# =========================

async def id(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        str(update.effective_chat.id)
    )
# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    teclado = [

        [
            InlineKeyboardButton("➕ Agregar Cliente", callback_data="menu_agregar")
        ],

        [
            InlineKeyboardButton("✏️ Modificar Cliente", callback_data="menu_modificar")
        ],

        [
            InlineKeyboardButton("🗑 Eliminar Cliente", callback_data="menu_eliminar")
        ],

        [
            InlineKeyboardButton("🔍 Buscar Cliente", callback_data="menu_buscar")
        ],

        [
            InlineKeyboardButton("📅 Ver Hoy", callback_data="ver_hoy")
        ],

        [
            InlineKeyboardButton("❌ Vencidas", callback_data="ver_vencidas")
        ],

        [
            InlineKeyboardButton("📊 Resumen", callback_data="resumen")
        ]

    ]

    await update.message.reply_text(

        "🤖 BOT RECORDATORIOS\n\n"

        "Selecciona una opción:",

        reply_markup=InlineKeyboardMarkup(teclado)

    )

# =========================
# TODO
# =========================

async def todo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    df = leer_datos()

    if df.empty:
        await update.message.reply_text("No hay datos")
        return

    mensaje = ""

    for _, row in df.iterrows():

        texto = (
            f"{row['Factura']} | "
            f"{row['Cliente']} | "
            f"{row['Servicio']} | "
            f"{row['Alerta']}\n"
        )

        if len(mensaje) + len(texto) > 4000:
            await update.message.reply_text(mensaje)
            mensaje = ""

        mensaje += texto

    if mensaje:
        await update.message.reply_text(mensaje)

# =========================
# VER ACTIVOS
# =========================

async def ver(update: Update, context: ContextTypes.DEFAULT_TYPE):

    df = leer_datos()

    activos = df[df["Dias_Restantes"] >= 0]

    if activos.empty:
        await update.message.reply_text("No hay activos")
        return

    mensaje = ""

    for _, row in activos.iterrows():

        mensaje += (
            f"👤 {row['Cliente']}\n"
            f"📺 {row['Servicio']}\n"
            f"⏳ {row['Alerta']}\n\n"
        )

    await update.message.reply_text(mensaje)

# =========================
# VENCIDAS
# =========================

async def vencidas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    df = leer_datos()

    vencidas = df[df["Dias_Restantes"] < 0]

    if vencidas.empty:
        await update.message.reply_text("✅ No hay vencidas")
        return

    mensaje = ""

    for _, row in vencidas.iterrows():

        mensaje += (
            f"❌ {row['Cliente']}\n"
            f"📺 {row['Servicio']}\n"
            f"⛔ {row['Alerta']}\n\n"
        )

    await update.message.reply_text(mensaje)

# =========================
# BUSCAR
# =========================

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Usa: /buscar nombre"
        )
        return

    texto = " ".join(context.args).lower()

    df = leer_datos()

    resultados = df[
        df["Cliente"]
        .astype(str)
        .str.lower()
        .str.contains(texto)
    ]

    if resultados.empty:
        await update.message.reply_text(
            "❌ No encontrado"
        )
        return

    for _, row in resultados.iterrows():

        mensaje = (
            f"🧾 {row['Factura']}\n"
            f"👤 {row['Cliente']}\n"
            f"📺 {row['Servicio']}\n"
            f"📅 {row['Fecha_Vencimiento'].date()}\n"
            f"⏳ {row['Alerta']}\n"
            f"🔑 {row['Cuenta']}\n"
        )

        await update.message.reply_text(mensaje)

# =========================
# TIPO
# =========================

async def tipo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Usa: /tipo spotify"
        )
        return

    servicio = " ".join(context.args).lower()

    df = leer_datos()

    resultados = df[
        df["Servicio"]
        .astype(str)
        .str.lower()
        .str.contains(servicio)
    ]

    if resultados.empty:
        await update.message.reply_text(
            "❌ No encontrado"
        )
        return

    for _, row in resultados.iterrows():

        mensaje = (
            f"👤 {row['Cliente']}\n"
            f"📺 {row['Servicio']}\n"
            f"🔑 {row['Cuenta']}\n"
        )

        await update.message.reply_text(mensaje)

# =========================
# CUENTAS
# =========================

async def cuentas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    df = leer_datos()

    mensaje = ""

    for _, row in df.iterrows():

        mensaje += (
            f"{row['Servicio']} → "
            f"{row['Cuenta']}\n"
        )

    await update.message.reply_text(
        mensaje[:4000]
    )

# =========================
# AGREGAR
# =========================

async def agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        texto = " ".join(context.args)

        partes = [
            x.strip()
            for x in texto.split("|")
        ]

        if len(partes) != 5:

            await update.message.reply_text(
                "Formato:\n"
                "/agregar nombre | fecha | dias | servicio | cuenta"
            )

            return

        nombre, fecha, dias, servicio, cuenta = partes

        factura = generar_factura()

        guardar_cliente(
            factura,
            nombre,
            fecha,
            dias,
            servicio,
            cuenta
        )

        await update.message.reply_text(
            f"✅ Cliente agregado\n\n"
            f"🧾 {factura}\n"
            f"👤 {nombre}"
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Error: {e}"
        )


# =========================
# CONVERSACION AGREGAR CLIENTE
# =========================


async def recibir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):

    datos_cliente["nombre"] = update.message.text

    await update.message.reply_text(
        "📺 Escribe el servicio:\n\n"
        "Ejemplo:\n"
        "Netflix"
    )

    return SERVICIO



async def recibir_servicio(update: Update, context: ContextTypes.DEFAULT_TYPE):

    datos_cliente["servicio"] = update.message.text

    await update.message.reply_text(
        "🔑 Escribe la cuenta:\n\n"
        "Ejemplo:\n"
        "correo@gmail.com"
    )

    return CUENTA



async def recibir_cuenta(update: Update, context: ContextTypes.DEFAULT_TYPE):

    datos_cliente["cuenta"] = update.message.text


    await update.message.reply_text(
        "⏳ ¿Cuántos días tendrá la cuenta?\n\n"
        "Ejemplo:\n"
        "30"
    )

    return DIAS



async def recibir_dias(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        dias = int(update.message.text)

        datos_cliente["dias"] = dias


        teclado = [
            [
                InlineKeyboardButton(
                    "📅 Hoy",
                    callback_data="fecha_hoy"
                )
            ]
        ]


        await update.message.reply_text(

            "📅 Escribe la fecha de inicio\n\n"
            "Formato:\n"
            "2026-07-16\n\n"
            "o presiona Hoy",

            reply_markup=InlineKeyboardMarkup(teclado)

        )

        return FECHA


    except:

        await update.message.reply_text(
            "❌ Escribe solamente números\nEjemplo: 30"
        )

        return DIAS




async def recibir_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):

    datos_cliente["fecha"] = update.message.text


    factura = generar_factura()


    datos_cliente["factura"] = factura


    mensaje = (

        "📋 CONFIRMAR CLIENTE\n\n"

        f"🧾 Factura: {factura}\n"
        f"👤 Cliente: {datos_cliente['nombre']}\n"
        f"📺 Servicio: {datos_cliente['servicio']}\n"
        f"🔑 Cuenta: {datos_cliente['cuenta']}\n"
        f"⏳ Días: {datos_cliente['dias']}\n"
        f"📅 Fecha: {datos_cliente['fecha']}\n"

    )


    teclado = [

        [
            InlineKeyboardButton(
                "✅ Guardar",
                callback_data="guardar_cliente"
            ),

            InlineKeyboardButton(
                "❌ Cancelar",
                callback_data="cancelar_cliente"
            )
        ]

    ]


    await update.message.reply_text(

        mensaje,

        reply_markup=InlineKeyboardMarkup(teclado)

    )


    return CONFIRMAR





async def boton_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()


    if query.data == "fecha_hoy":

        datos_cliente["fecha"] = datetime.now().strftime(
            "%Y-%m-%d"
        )


        factura = generar_factura()

        datos_cliente["factura"] = factura


        mensaje = (

            "📋 CONFIRMAR CLIENTE\n\n"

            f"🧾 Factura: {factura}\n"
            f"👤 Cliente: {datos_cliente['nombre']}\n"
            f"📺 Servicio: {datos_cliente['servicio']}\n"
            f"🔑 Cuenta: {datos_cliente['cuenta']}\n"
            f"⏳ Días: {datos_cliente['dias']}\n"
            f"📅 Fecha: {datos_cliente['fecha']}\n"

        )


        teclado = [
            [
                InlineKeyboardButton(
                    "✅ Guardar",
                    callback_data="guardar_cliente"
                ),

                InlineKeyboardButton(
                    "❌ Cancelar",
                    callback_data="cancelar_cliente"
                )
            ]
        ]


        await query.message.reply_text(

            mensaje,

            reply_markup=InlineKeyboardMarkup(teclado)

        )

        return CONFIRMAR




async def confirmar_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()


    if query.data == "guardar_cliente":


        guardar_cliente(

            datos_cliente["factura"],

            datos_cliente["nombre"],

            datos_cliente["fecha"],

            datos_cliente["dias"],

            datos_cliente["servicio"],

            datos_cliente["cuenta"]

        )


        await query.message.reply_text(

            "✅ Cliente guardado correctamente\n\n"

            f"🧾 {datos_cliente['factura']}"

        )


        datos_cliente.clear()


        return ConversationHandler.END



    if query.data == "cancelar_cliente":


        datos_cliente.clear()


        await query.message.reply_text(

            "❌ Registro cancelado"

        )


        return ConversationHandler.END
# =========================
# ELIMINAR
# =========================

async def eliminar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        await update.message.reply_text(
            "Usa: /eliminar Fact_001"
        )

        return

    factura = context.args[0]

    df = leer_datos()

    nuevo_df = df[
        df["Factura"] != factura
    ]

    if len(df) == len(nuevo_df):

        await update.message.reply_text(
            "❌ Factura no encontrada"
        )

        return

    nuevo_df = nuevo_df[[
        "Factura",
        "Cliente",
        "Fecha_Emision",
        "Dias",
        "Servicio",
        "Cuenta"
    ]]

    nuevo_df.to_csv(
        CSV_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    await update.message.reply_text(
        f"🗑 Eliminado: {factura}"
    )

# =========================
# MODIFICAR
# =========================

async def modificar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:

        texto = " ".join(context.args)

        partes = [
            x.strip()
            for x in texto.split("|")
        ]

        if len(partes) != 6:

            await update.message.reply_text(
                "Formato:\n"
                "/modificar Fact_001 | nombre | fecha | dias | servicio | cuenta"
            )

            return

        factura, nombre, fecha, dias, servicio, cuenta = partes

        df = leer_datos()

        # Buscar factura
        indice = df[
            df["Factura"] == factura
        ].index

        if len(indice) == 0:

            await update.message.reply_text(
                "❌ Factura no encontrada"
            )

            return

        i = indice[0]

        # Modificar datos
        df.at[i, "Cliente"] = nombre
        df.at[i, "Fecha_Emision"] = fecha
        df.at[i, "Dias"] = dias
        df.at[i, "Servicio"] = servicio
        df.at[i, "Cuenta"] = cuenta

        # Guardar
        df = df[[
            "Factura",
            "Cliente",
            "Fecha_Emision",
            "Dias",
            "Servicio",
            "Cuenta"
        ]]

        df.to_csv(
            CSV_FILE,
            index=False,
            encoding="utf-8-sig"
        )

        await update.message.reply_text(
            f"✅ Factura modificada\n\n"
            f"🧾 {factura}"
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Error: {e}"
        )
        
        
# =========================
# INICIAR MODIFICAR
# =========================

async def iniciar_modificar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    await query.message.reply_text(
        "🔎 Escribe el nombre del cliente:"
    )

    return MOD_NOMBRE        
###################
#########MODIFICAR CLIENTE
#=========================
async def recibir_nombre_modificar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    nombre = update.message.text.strip().lower()

    df = leer_datos()

    resultados = df[
        df["Cliente"]
        .astype(str)
        .str.lower()
        .str.contains(nombre, na=False)
    ]

    if resultados.empty:

        await update.message.reply_text(
            "❌ No encontré clientes."
        )

        return ConversationHandler.END

    teclado = []

    mensaje = "👥 CLIENTES ENCONTRADOS\n\n"

    for indice, fila in resultados.iterrows():

        mensaje += (
            f"🧾 {fila['Factura']}\n"
            f"👤 {fila['Cliente']}\n"
            f"📺 {fila['Servicio']}\n"
            f"📅 Inicio: {fila['Fecha_Emision'].date()}\n\n"
        )

        teclado.append([
            InlineKeyboardButton(
                f"{fila['Factura']} | {fila['Servicio']}",
                callback_data=f"modificar_indice_{indice}"
            )
        ])

    await update.message.reply_text(
        mensaje,
        reply_markup=InlineKeyboardMarkup(teclado)
    )

    return MOD_FACTURA

async def seleccionar_factura_modificar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    try:

        indice = int(
            query.data.replace(
                "modificar_indice_",
                ""
            )
        )

    except ValueError:

        await query.message.reply_text(
            "❌ No fue posible seleccionar el cliente."
        )

        return ConversationHandler.END

    df = leer_datos()

    if indice not in df.index:

        await query.message.reply_text(
            "❌ El cliente seleccionado ya no existe."
        )

        return ConversationHandler.END

    fila = df.loc[indice]

    datos_cliente["indice_modificar"] = indice
    datos_cliente["factura_modificar"] = str(fila["Factura"])

    mensaje = (

        "📋 CLIENTE SELECCIONADO\n\n"

        f"🧾 {fila['Factura']}\n"
        f"👤 {fila['Cliente']}\n"
        f"📺 {fila['Servicio']}\n"
        f"🔑 {fila['Cuenta']}\n"
        f"📅 Inicio: {fila['Fecha_Emision'].date()}\n"
        f"⏳ {fila['Dias']} días\n\n"

        "¿Qué deseas modificar?"
    )

    teclado = [

        [
            InlineKeyboardButton(
                "⏳ Renovar días",
                callback_data="accion_dias"
            )
        ],

        [
            InlineKeyboardButton(
                "🔑 Cambiar cuenta",
                callback_data="accion_cuenta"
            )
        ],

        [
            InlineKeyboardButton(
                "📅 Cambiar fecha",
                callback_data="accion_fecha"
            )
        ],

        [
            InlineKeyboardButton(
                "📺 Cambiar servicio",
                callback_data="accion_servicio"
            )
        ],

        [
            InlineKeyboardButton(
                "👤 Cambiar nombre",
                callback_data="accion_cliente"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ Cancelar",
                callback_data="accion_cancelar"
            )
        ]

    ]

    await query.message.reply_text(
        mensaje,
        reply_markup=InlineKeyboardMarkup(teclado)
    )

    return MOD_ACCION

# ==========================================
# SELECCIONAR QUÉ DATO SE VA A MODIFICAR
# ==========================================

async def seleccionar_accion_modificar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    accion = query.data

    if accion == "accion_dias":

        await query.message.reply_text(
            "⏳ Escribe la nueva cantidad de días:\n\n"
            "Ejemplo: 30"
        )

        return MOD_DIAS

    elif accion == "accion_cuenta":

        await query.message.reply_text(
            "🔑 Escribe la nueva cuenta:"
        )

        return MOD_CUENTA

    elif accion == "accion_fecha":

        await query.message.reply_text(
            "📅 Escribe la nueva fecha de inicio:\n\n"
            "Formato: 2026-07-29"
        )

        return MOD_FECHA

    elif accion == "accion_servicio":

        await query.message.reply_text(
            "📺 Escribe el nuevo servicio:"
        )

        return MOD_SERVICIO

    elif accion == "accion_cliente":

        await query.message.reply_text(
            "👤 Escribe el nuevo nombre del cliente:"
        )

        return MOD_CLIENTE

    elif accion == "accion_cancelar":

        datos_cliente.clear()

        await query.message.reply_text(
            "❌ Modificación cancelada."
        )

        return ConversationHandler.END


# ==========================================
# GUARDAR UNA MODIFICACIÓN EN EL CSV
# ==========================================

async def guardar_modificacion(
    update: Update,
    columna: str,
    valor
):

    indice = datos_cliente.get("indice_modificar")
    factura = datos_cliente.get("factura_modificar")

    if indice is None:

        await update.message.reply_text(
            "❌ No hay un cliente seleccionado.\n"
            "Inicia nuevamente con /start."
        )

        return ConversationHandler.END

    df = leer_datos()

    if indice not in df.index:

        await update.message.reply_text(
            "❌ El cliente seleccionado ya no existe."
        )

        datos_cliente.clear()

        return ConversationHandler.END

    # Modificar exactamente la fila seleccionada
    df.at[indice, columna] = valor

    df_guardar = df[[
        "Factura",
        "Cliente",
        "Fecha_Emision",
        "Dias",
        "Servicio",
        "Cuenta"
    ]].copy()

    df_guardar["Fecha_Emision"] = pd.to_datetime(
        df_guardar["Fecha_Emision"],
        errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    df_guardar.to_csv(
        CSV_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    await update.message.reply_text(
        "✅ Cliente modificado correctamente\n\n"
        f"🧾 Factura: {factura}\n"
        f"✏️ Campo modificado: {columna}\n"
        f"🆕 Nuevo valor: {valor}"
    )

    datos_cliente.clear()

    return ConversationHandler.END


# ==========================================
# RECIBIR NUEVOS DÍAS
# ==========================================
async def recibir_dias_modificar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        nuevos_dias = int(update.message.text.strip())

        if nuevos_dias <= 0:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ Escribe una cantidad válida de días.\n\n"
            "Ejemplo: 30"
        )

        return MOD_DIAS

    indice = datos_cliente.get("indice_modificar")
    factura = datos_cliente.get("factura_modificar")

    if indice is None:

        await update.message.reply_text(
            "❌ No hay un cliente seleccionado.\n"
            "Inicia nuevamente con /start."
        )

        return ConversationHandler.END

    df = leer_datos()

    if indice not in df.index:

        await update.message.reply_text(
            "❌ El cliente seleccionado ya no existe."
        )

        datos_cliente.clear()

        return ConversationHandler.END

    # Fecha actual de México
    fecha_hoy = datetime.now(
        ZoneInfo("America/Mexico_City")
    ).strftime("%Y-%m-%d")

    # Renovar días y reiniciar la fecha desde hoy
    df.at[indice, "Dias"] = nuevos_dias
    df.at[indice, "Fecha_Emision"] = fecha_hoy

    df_guardar = df[[
        "Factura",
        "Cliente",
        "Fecha_Emision",
        "Dias",
        "Servicio",
        "Cuenta"
    ]].copy()

    df_guardar["Fecha_Emision"] = pd.to_datetime(
        df_guardar["Fecha_Emision"],
        errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    df_guardar.to_csv(
        CSV_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    fecha_vencimiento = (
        pd.Timestamp(fecha_hoy) +
        pd.Timedelta(days=nuevos_dias)
    ).strftime("%Y-%m-%d")

    await update.message.reply_text(
        "✅ Cliente renovado correctamente\n\n"
        f"🧾 Factura: {factura}\n"
        f"📅 Nuevo inicio: {fecha_hoy}\n"
        f"⏳ Nuevos días: {nuevos_dias}\n"
        f"📆 Nuevo vencimiento: {fecha_vencimiento}"
    )

    datos_cliente.clear()

    return ConversationHandler.END

# ==========================================
# RECIBIR NUEVA CUENTA
# ==========================================

async def recibir_cuenta_modificar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    nueva_cuenta = update.message.text.strip()

    if not nueva_cuenta:

        await update.message.reply_text(
            "❌ La cuenta no puede estar vacía."
        )

        return MOD_CUENTA

    return await guardar_modificacion(
        update,
        "Cuenta",
        nueva_cuenta
    )


# ==========================================
# RECIBIR NUEVA FECHA
# ==========================================

async def recibir_fecha_modificar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    texto_fecha = update.message.text.strip()

    try:

        nueva_fecha = datetime.strptime(
            texto_fecha,
            "%Y-%m-%d"
        ).strftime("%Y-%m-%d")

    except ValueError:

        await update.message.reply_text(
            "❌ Fecha inválida.\n\n"
            "Usa este formato:\n"
            "2026-07-29"
        )

        return MOD_FECHA

    return await guardar_modificacion(
        update,
        "Fecha_Emision",
        nueva_fecha
    )


# ==========================================
# RECIBIR NUEVO SERVICIO
# ==========================================

async def recibir_servicio_modificar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    nuevo_servicio = update.message.text.strip()

    if not nuevo_servicio:

        await update.message.reply_text(
            "❌ El servicio no puede estar vacío."
        )

        return MOD_SERVICIO

    return await guardar_modificacion(
        update,
        "Servicio",
        nuevo_servicio
    )


# ==========================================
# RECIBIR NUEVO NOMBRE
# ==========================================

async def recibir_cliente_modificar(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    nuevo_nombre = update.message.text.strip()

    if not nuevo_nombre:

        await update.message.reply_text(
            "❌ El nombre no puede estar vacío."
        )

        return MOD_CLIENTE

    return await guardar_modificacion(
        update,
        "Cliente",
        nuevo_nombre
    )
# =========================
async def probar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await revisar_vencimientos(context)
    
async def revisar_vencimientos(context: ContextTypes.DEFAULT_TYPE):

    df = leer_datos()

    hoy = df[df["Dias_Restantes"] == 0]
    vencidas = df[df["Dias_Restantes"] < 0]

    mensaje = (
        "🚨 RECORDATORIO DE FACTURAS\n\n"
        f"📅 Hoy vencen: {len(hoy)}\n"
        f"❌ Vencidas: {len(vencidas)}"
    )

    teclado = [
        [InlineKeyboardButton("📅 Ver hoy", callback_data="ver_hoy")],
        [InlineKeyboardButton("❌ Ver vencidas", callback_data="ver_vencidas")],
        [InlineKeyboardButton("📊 Resumen", callback_data="resumen")]
    ]

    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=mensaje,
        reply_markup=InlineKeyboardMarkup(teclado)
    )

async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    opcion = query.data

    if opcion == "menu_agregar":

        await query.message.reply_text(
            "👤 Escribe el nombre del cliente:"
        )

        return NOMBRE

    if opcion == "menu_eliminar":

        await query.message.reply_text(
            "🗑 Para eliminar utiliza:\n\n"
            "/eliminar Fact_001"
        )

        return

    if opcion == "menu_buscar":

        await query.message.reply_text(
            "🔍 Para buscar utiliza:\n\n"
            "/buscar nombre"
        )

        return

    df = leer_datos()

    # =====================
    # VER HOY
    # =====================

    if opcion == "ver_hoy":

        hoy = df[df["Dias_Restantes"] == 0]

        if hoy.empty:

            await query.edit_message_text(
                "✅ Hoy no vence ninguna factura."
            )

            return

        mensaje = "📅 FACTURAS QUE VENCEN HOY\n\n"

        for _, row in hoy.iterrows():

            mensaje += (
                f"🧾 {row['Factura']}\n"
                f"👤 {row['Cliente']}\n"
                f"📺 {row['Servicio']}\n\n"
            )

        await query.edit_message_text(mensaje)

        return

    # =====================
    # VENCIDAS
    # =====================

    if opcion == "ver_vencidas":

        vencidas = df[df["Dias_Restantes"] < 0]

        if vencidas.empty:

            await query.edit_message_text(
                "✅ No hay facturas vencidas."
            )

            return

        mensaje = (
            f"❌ FACTURAS VENCIDAS ({len(vencidas)})\n\n"
        )

        for _, row in vencidas.iterrows():

            mensaje += (
                f"🧾 {row['Factura']}\n"
                f"👤 {row['Cliente']}\n"
                f"📺 {row['Servicio']}\n"
                f"{row['Alerta']}\n\n"
            )

        await query.edit_message_text(mensaje)

        return

    # =====================
    # RESUMEN
    # =====================

    if opcion == "resumen":

        activos = len(df[df["Dias_Restantes"] >= 0])

        vencidas = len(df[df["Dias_Restantes"] < 0])

        hoy = len(df[df["Dias_Restantes"] == 0])

        proximas = len(
            df[
                (df["Dias_Restantes"] > 0)
                &
                (df["Dias_Restantes"] <= 3)
            ]
        )

        mensaje = (
            "📊 RESUMEN GENERAL\n\n"
            f"👥 Clientes: {len(df)}\n\n"
            f"📅 Vencen hoy: {hoy}\n"
            f"⚠️ Próximas (3 días): {proximas}\n"
            f"❌ Vencidas: {vencidas}\n"
            f"✅ Activas: {activos}"
        )

        await query.edit_message_text(mensaje)
        
# BOT
# =========================

app = (
    ApplicationBuilder()
    .token(TOKEN)
    .build()
)

job_queue = app.job_queue

job_queue.run_daily(
    revisar_vencimientos,
    time=time(
        hour=12,
        minute=3,
        tzinfo=ZoneInfo("America/Mexico_City")
    )
)

conv_agregar = ConversationHandler(

    entry_points=[
        CallbackQueryHandler(
            botones,
            pattern="^menu_agregar$"
        )
    ],


    states={

        NOMBRE:[
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_nombre
            )
        ],


        SERVICIO:[
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_servicio
            )
        ],


        CUENTA:[
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_cuenta
            )
        ],


        DIAS:[
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_dias
            )
        ],


        FECHA:[
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_fecha
            ),

            CallbackQueryHandler(
                boton_fecha,
                pattern="^fecha_hoy$"
            )
        ],


        CONFIRMAR:[
            CallbackQueryHandler(
                confirmar_cliente,
                pattern="^(guardar_cliente|cancelar_cliente)$"
            )
        ]

    },


    fallbacks=[]

)

conv_modificar = ConversationHandler(

    entry_points=[

        CallbackQueryHandler(
            iniciar_modificar,
            pattern="^menu_modificar$"
        )

    ],

    states={

        MOD_NOMBRE: [

            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_nombre_modificar
            )

        ],

        MOD_FACTURA: [

            CallbackQueryHandler(
                seleccionar_factura_modificar,
                pattern="^modificar_indice_"
            )

        ],

        MOD_ACCION: [

            CallbackQueryHandler(
                seleccionar_accion_modificar,
                pattern="^accion_"
            )

        ],

        MOD_DIAS: [

            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_dias_modificar
            )

        ],

        MOD_CUENTA: [

            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_cuenta_modificar
            )

        ],

        MOD_FECHA: [

            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_fecha_modificar
            )

        ],

        MOD_SERVICIO: [

            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_servicio_modificar
            )

        ],

        MOD_CLIENTE: [

            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                recibir_cliente_modificar
            )

        ]

    },

    fallbacks=[],

    allow_reentry=True
)


app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("todo", todo))
app.add_handler(CommandHandler("ver", ver))
app.add_handler(CommandHandler("vencidas", vencidas))
app.add_handler(CommandHandler("buscar", buscar))
app.add_handler(CommandHandler("tipo", tipo))
app.add_handler(CommandHandler("cuentas", cuentas))
app.add_handler(CommandHandler("agregar", agregar))
app.add_handler(CommandHandler("eliminar", eliminar))
app.add_handler(CommandHandler("modificar", modificar))
app.add_handler(CommandHandler("id", id))
app.add_handler(conv_agregar)
app.add_handler(conv_modificar)
app.add_handler(
    CallbackQueryHandler(
        botones
    )
)

app.add_handler(CommandHandler("probar", probar))

print("✅ Bot corriendo...")
app.run_polling()
