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

NOMBRE, SERVICIO, CUENTA, DIAS, FECHA, CONFIRMAR, MOD_NOMBRE, MOD_FACTURA, MOD_ACCION, MOD_DIAS = range(10)
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
# MODIFICAR POR NOMBRE
# =========================


async def iniciar_modificar(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()


    await query.message.reply_text(

        "🔎 Escribe el nombre del cliente:\n\n"
        "Ejemplo:\n"
        "Juan"

    )


    return MOD_NOMBRE

#################def##############

async def recibir_nombre_modificar(update: Update, context: ContextTypes.DEFAULT_TYPE):


    nombre = update.message.text.strip()


    df = leer_datos()


    resultados = df[
        df["Cliente"]
        .astype(str)
        .str.lower()
        .str.contains(nombre.lower())
    ]


    if resultados.empty:


        await update.message.reply_text(

            "❌ No encontré ningún cliente"

        )

        return ConversationHandler.END



    datos_cliente["busqueda_modificar"] = nombre


    teclado = []


    mensaje = "📋 HISTORIAL DEL CLIENTE\n\n"


    for _, row in resultados.iterrows():


        factura = row["Factura"]


        texto_boton = (
            f"🧾 {factura} | {row['Servicio']}"
        )


        teclado.append([

            InlineKeyboardButton(

                texto_boton,

                callback_data=f"modificar_{factura}"

            )

        ])



        mensaje += (

            f"🧾 {factura}\n"
            f"📺 {row['Servicio']}\n"
            f"🔑 {row['Cuenta']}\n"
            f"📅 {row['Fecha_Vencimiento'].date()}\n\n"

        )



    await update.message.reply_text(

        mensaje,

        reply_markup=InlineKeyboardMarkup(teclado)

    )


    return MOD_FACTURA

async def seleccionar_factura_modificar(update: Update, context: ContextTypes.DEFAULT_TYPE):


    query = update.callback_query

    await query.answer()


    factura = query.data.replace(
        "modificar_",
        ""
    )


    datos_cliente["factura_modificar"] = factura



    df = leer_datos()


    fila = df[
        df["Factura"] == factura
    ].iloc[0]



    mensaje = (

        "📋 FACTURA SELECCIONADA\n\n"

        f"🧾 {fila['Factura']}\n"
        f"👤 {fila['Cliente']}\n"
        f"📺 {fila['Servicio']}\n"
        f"🔑 {fila['Cuenta']}\n\n"

        "¿Qué deseas modificar?"

    )


    teclado = [

        [

            InlineKeyboardButton(

                "🔄 Renovar tiempo",

                callback_data="accion_renovar"

            )

        ],

        [

            InlineKeyboardButton(

                "✏️ Cambiar cuenta",

                callback_data="accion_cuenta"

            )

        ],

        [

            InlineKeyboardButton(

                "📝 Editar datos",

                callback_data="accion_datos"

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


        MOD_NOMBRE:[

            MessageHandler(

                filters.TEXT & ~filters.COMMAND,

                recibir_nombre_modificar

            )

        ],


        MOD_FACTURA:[

            CallbackQueryHandler(

                seleccionar_factura_modificar,

                pattern="^modificar_"

            )

        ],


        MOD_ACCION:[

            CallbackQueryHandler(

                seleccionar_factura_modificar

            )

        ]

    },


    fallbacks=[]

)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("todo", todo))
app.add_handler(CommandHandler("ver", ver))
app.add_handler(CommandHandler("vencidas", vencidas))
app.add_handler(CommandHandler("buscar", buscar))
app.add_handler(CommandHandler("tipo", tipo))
app.add_handler(CommandHandler("cuentas", cuentas))
app.add_handler(CommandHandler("agregar", agregar))
app.add_handler(conv_modificar)
app.add_handler(CommandHandler("eliminar", eliminar))
app.add_handler(CommandHandler("modificar", modificar))
app.add_handler(CommandHandler("id", id))
app.add_handler(conv_agregar)

app.add_handler(
    CallbackQueryHandler(
        botones
    )
)
app.add_handler(CommandHandler("probar", probar))

print("✅ Bot corriendo...")
app.run_polling()
