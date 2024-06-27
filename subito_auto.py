import requests
import pandas as pd
import time
import traceback
from bs4 import BeautifulSoup
import utils
import utils_subito

def extract_data(soup):
    titolo_list=[]
    town_list=[]
    prezzo_list=[]
    data_list=[]
    km_list=[]
    motorizzazione_list=[]
    sito_list=[]
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
            else:
                citta = annuncio.find("div").text.strip()
                titolo_list.append(titolo)
                town_list.append(citta)
                for elem in annuncio.find_all("p"):
                    elem = elem.text.strip()
                    if '€' in elem:
                        prezzo = int(elem.split('\xa0€')[0].replace(".", ""))
                    if '/' in elem:
                        anno = int(elem.split('/')[1])
                    if 'Km' in elem:
                        if 'Km 0 km' in elem:
                            km = 0
                        else:
                            km = int(elem.split(' ')[0])
                    if elem in ['Benzina', 'Gpl', 'Diesel', 'Metano', 'Ibrida', 'Elettrica','Altro']:
                        motorizzazione = elem
                prezzo_list.append(prezzo)
                data_list.append(anno)
                km_list.append(km)
                motorizzazione_list.append(motorizzazione)  
    except Exception as e:
        logger.error(e)
    return titolo_list, town_list, prezzo_list, data_list, km_list, motorizzazione_list, sito_list


def run_loop(nome_file_csv, dtype, columns, seconds_to_sleep=60):
    while (1):
        try:
            df_tot = utils_subito.read_if_file_exists(nome_file_csv,dtype, columns)
            df_tot['nuovo']=0
            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser")
        except Exception as e:
            logger.error(e)
            time.sleep(60*5)
        try:
            titolo_list, town_list, prezzo_list, data_list, km_list, motorizzazione_list, sito_list = extract_data(soup)
        except Exception as e:
            logger.error(e)    
        try:
            df = pd.DataFrame({'nome':titolo_list,
                            'citta':town_list,
                            'prezzo':prezzo_list,
                            'data':data_list,
                            'km':km_list,
                            'motorizzazione':motorizzazione_list,
                            'sito':sito_list,
                            'nuovo':[1]*len(titolo_list)})
            
            df = df[(df['km']>km_da) & (df['motorizzazione']!=motorizzazione_diversa_da)]
            df['valore_effettivo'] = 100/(df['km']/3100000) + (df['data']-2000)*175
            df['convenienza'] = df['valore_effettivo'] - df['prezzo']
            df_tot = pd.concat([df_tot, df])
            df_tot = df_tot.drop_duplicates(['nome','citta','prezzo','data','km'],keep= 'first')
            df_tot.fillna(99999999)
            df_tot = df_tot.sort_values(by='convenienza', ascending=False)

            df_send = df_tot[(df_tot['nuovo']==1) & (df_tot['convenienza']> convenienza_maggiore)]
            df_send.apply(lambda row: utils.send_message(row['nome'] + ', ' + str(row['prezzo']) + ' euro, ' + str(row['km']) + 'km, anno '+ str(row['data']) + ' convenienza'+  str(row['convenienza']) + ' '+  row['sito'], 
                                                            token, 
                                                            chat_id), axis = 1)

            df_tot = df_tot.drop(columns=['nuovo'])
            df_tot.to_csv(nome_file_csv, sep=';',index=False)
        except Exception:
            traceback.print_exc()
        time.sleep(seconds_to_sleep)

logger = utils.set_log('./subito_auto.log', 'info', 'subito_affitti')

json_data = utils.read_json_file('./config.json')
token, chat_id =  utils.read_account_info(json_data)

url = f'https://www.subito.it/annunci-lombardia/vendita/auto/?ys={json_data["year_min"]}&ye={json_data["year_max"]}&ps={json_data["price_min"]}&pe={json_data["price_max"]}&me=25'
nome_file_csv = 'auto.csv'
string_start = '>Annunci in Auto in Lombardia<'
km_da = 20000
motorizzazione_diversa_da = 'Diesel'
convenienza_maggiore = 1000

dtype = {'name': str,
         'citta': str,
        'prezzo': 'float64',
        'data':'Int64',
        'km':'Int64',
        'motorizzazione':str,
        'sito':str,
        'valore_effettivo':'float64',
        'convenienza':'float64'}
columns=['nome','citta','prezzo','data','km','motorizzazione',
                              'sito','nuovo','valore_effettivo','convenienza']



run_loop(nome_file_csv, dtype, columns)