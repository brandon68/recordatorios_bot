import pandas as pd
import csv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

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

    mensaje = (
        "🤖 BOT DE RECORDATORIOS\n\n"

        "📌 COMANDOS:\n\n"

        "/todo → Ver todo\n"
        "/ver → Ver activos\n"
        "/vencidas → Ver vencidas\n"
        "/buscar nombre\n"
        "/tipo spotify\n"
        "/cuentas\n"
        "/agregar nombre | fecha | dias | servicio | cuenta\n"
        "/eliminar Fact_001\n"
        "/modificar Fact_001 | nombre | fecha | dias | servicio | cuenta\n"
    )

    await update.message.reply_text(mensaje)

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
# BOT
# =========================

app = (
    ApplicationBuilder()
    .token(TOKEN)
    .build()
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

print("✅ Bot corriendo...")
app.run_polling()
