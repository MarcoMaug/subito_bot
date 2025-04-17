import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import utils
import utils_subito
import os
import logging
from logging.handlers import RotatingFileHandler
import asyncio  # Import necessario

def send_message(row, chat_id):
    message = row['nome'] + ', ' + str(row['prezzo']) + ' euro, ' + str(row['km']) + 'km, anno '+ str(row['data']) + ' convenienza'+  str(row['convenienza']) + ' '+  row['sito']
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url).json()
    return 1

async def run_loop(context: ContextTypes.DEFAULT_TYPE):
    global stop_bot, url
    dtype = {
        'nome': str, 'citta': str, 'prezzo': 'float64',
        'data': 'Int64', 'km': 'Int64', 'motorizzazione': str,
        'sito': str, 'valore_effettivo': 'float64', 'convenienza': 'float64'
    }
    columns = ['nome', 'citta', 'prezzo', 'data', 'km', 'motorizzazione', 'sito', 'nuovo', 'valore_effettivo', 'convenienza']
    seconds_to_sleep = 300

    while not stop_bot:
        try:
            # Leggi o crea il DataFrame
            df_tot = utils_subito.read_if_file_exists(nome_file_csv, dtype, columns)
            df_tot['nuovo'] = 0

            # Effettua il scraping
            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser")
            titolo_list, town_list, prezzo_list, data_list, km_list, motorizzazione_list, sito_list = extract_data(soup)
            
            # Crea il DataFrame aggiornato
            df = pd.DataFrame({
                'nome': titolo_list, 'citta': town_list, 'prezzo': prezzo_list,
                'data': data_list, 'km': km_list, 'motorizzazione': motorizzazione_list,
                'sito': sito_list, 'nuovo': [1] * len(titolo_list)
            })

            # Calcola i valori e salva su CSV
            df['valore_effettivo'] = 100 / (df['km'] / 3100000) + (df['data'] - 2000) * 175
            df['convenienza'] = df['valore_effettivo'] - df['prezzo']
            df_tot = pd.concat([df_tot, df]).drop_duplicates(['nome', 'citta', 'prezzo', 'data', 'km'], keep='first')
            df_tot.to_csv(nome_file_csv, sep=';', index=False)

            df_send = df_tot[(df_tot['nuovo']==1) & (df_tot['convenienza']> convenienza_maggiore)]
            df_send.apply(lambda x: send_message(x, chat_id), axis = 1)


        except Exception as e:
            print(f"Error in run_loop: {e}")
        
        # Usa asyncio.sleep per permettere l'interruzione
        await asyncio.sleep(seconds_to_sleep)

# Percorso del file di log
log_file = os.path.join(os.path.dirname(__file__), "bot.log")

# Configurazione del RotatingFileHandler
handler = RotatingFileHandler(
    log_file, maxBytes=10 * 1024 * 1024, backupCount=5
)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Configurazione del logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

# Variabili globali
json_data = utils.read_json_file('./config.json')
token, chat_id = utils.read_account_info(json_data)

url = "https://www.subito.it/annunci-italia/vendita/auto/?cvs=1&ys=2013&ps=2000&pe=8000&me=22"
nome_file_csv = 'auto_new.csv'
km_da = 0
motorizzazione_diversa_da = ''
convenienza_maggiore = -999999
stop_bot = False

# Funzione per estrarre dati dal sito
def extract_data(soup):
    logger.debug("Inizio estrazione dati da HTML.")
    titolo_list = []
    town_list = []
    prezzo_list = []
    data_list = []
    km_list = []
    motorizzazione_list = []
    sito_list = []
    try:
        annunci = soup.find_all("div", class_='BigCard-module_upper-data-group__H2CEM')
        siti = soup.find_all("a", class_="BigCard-module_link__kVqPE")
        for sito in siti:
            sito = sito['href']
            sito_list.append(sito)
        
        for annuncio in annunci:
            titolo = annuncio.find("h2").text.strip()
            if titolo.lower() in ['smart']:
                continue
            citta = annuncio.find("div").text.strip()
            titolo_list.append(titolo)
            town_list.append(citta)
            prezzo, anno, km, motorizzazione = None, None, None, None
            for elem in annuncio.find_all("p"):
                elem = elem.text.strip()
                if '€' in elem:
                    prezzo = int(elem.split('\xa0€')[0].replace(".", ""))
                if '/' in elem:
                    anno = int(elem.split('/')[1])
                if 'Km' in elem:
                    km = 0 if 'Km 0 km' in elem else int(elem.split(' ')[0])
                if elem in ['Benzina', 'Gpl', 'Diesel', 'Metano', 'Ibrida', 'Elettrica', 'Altro']:
                    motorizzazione = elem
            prezzo_list.append(prezzo)
            data_list.append(anno)
            km_list.append(km)
            motorizzazione_list.append(motorizzazione)
    except Exception as e:
        logger.error(f"Errore durante l'estrazione dei dati: {e}")
    return titolo_list, town_list, prezzo_list, data_list, km_list, motorizzazione_list, sito_list

# Funzione di avvio
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Comando /start ricevuto.")
    keyboard = [
        [InlineKeyboardButton("Nuovo URL", callback_data='new_url')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Bot avviato. Usa i pulsanti per gestire il bot:", reply_markup=reply_markup)

# Gestore dei pulsanti
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stop_bot
    query = update.callback_query
    await query.answer()
    if query.data == 'new_url':
        logger.info("Richiesta di nuovo URL ricevuta.")
        await query.edit_message_text("Inserisci il nuovo URL usando il comando /set_url <nuovo_url>.")

# Comando per impostare un nuovo URL
async def set_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global url
    try:
        new_url = context.args[0]
        if new_url.startswith("https://"):
            url = new_url
            logger.info(f"URL aggiornato a: {url}")
            await update.message.reply_text(f"URL aggiornato a: {url}")
        else:
            logger.warning("Tentativo di aggiornare l'URL con un valore non valido.")
            await update.message.reply_text("URL non valido. Deve iniziare con 'https://'.")
    except IndexError:
        logger.warning("Comando /set_url usato senza fornire un URL.")
        await update.message.reply_text("Usa il comando /set_url <nuovo_url>.")

# Comando per fermare il bot
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global stop_bot
    stop_bot = True
    logger.info("Il bot è stato fermato tramite il comando /stop.")
    await update.message.reply_text("Il bot è stato fermato.")

# Avvio del bot
if __name__ == "__main__":
    logger.info("Avvio del bot.")
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("set_url", set_url))
    application.add_handler(CommandHandler("stop", stop))

    # Esegui il ciclo asincrono per l'aggiornamento dei dati
    loop = asyncio.get_event_loop()
    loop.create_task(run_loop(application))
    application.run_polling()
