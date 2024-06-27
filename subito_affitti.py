import requests
import pandas as pd
import time

import traceback
from bs4 import BeautifulSoup
import utils
import utils_subito

logger = utils.set_log('./subito_affitti.log', 'info', 'subito_affitti')


def extract_data(soup):
    titolo_list=[]
    town_list=[]
    prezzo_list=[]
    sito_list=[]
    siti = soup.find_all("a", class_="BigCard-module_link__kVqPE")
    for sito in siti:
        sito = sito['href']
        sito_list.append(sito)
    annunci = soup.find_all("div", class_='BigCard-module_upper-data-group__H2CEM')
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
                    print(elem)
                    prezzo = int(elem.split('€')[0].replace(".", ""))
            prezzo_list.append(prezzo)
    return titolo_list, town_list, prezzo_list, sito_list

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
            titolo_list, town_list, prezzo_list, sito_list = extract_data(soup)
        except Exception as e:
            logger.error(e)
        try:
            df = pd.DataFrame({'nome':titolo_list,
                                'citta':town_list,
                                'prezzo':prezzo_list,
                                'sito':sito_list,
                                'nuovo':[1]*len(titolo_list)})
            
            df_tot = pd.concat([df_tot, df])
            df_tot = df_tot.drop_duplicates(['nome','prezzo', 'citta'],keep= 'first')
            df_tot.fillna(99999999)

            df_send = df_tot[(df_tot['nuovo']==1)]
            df_send.apply(lambda row: utils.send_message(row['nome'] + ', ' + str(row['prezzo']) + ' euro, ' + str(row['citta']) + ' ' + row['sito'], 
                                                        token, 
                                                        chat_id), 
                                                        axis = 1)

            df_tot = df_tot.drop(columns=['nuovo'])
            df_tot.to_csv(nome_file_csv, sep=';',index=False)
        except Exception:
            traceback.print_exc()
        logger.info("loop eseguito")
        
    time.sleep(seconds_to_sleep)



dtype = {'name': str,'citta': str,
         'prezzo': 'float64',
         'data':'Int64',
         'sito':str,
        }
columns = ['nome','citta','prezzo','sito','nuovo']
json_data = utils.read_json_file('./config.json')
token, chat_id =  utils.read_account_info(json_data)

url = f'https://www.subito.it/annunci-locali/affitto/appartamenti/?q=appartamento&rad=7500&lat=45.57122&lon=9.15921&ps={json_data["price_min"]}&pe={json_data["price_max"]}'
nome_file_csv = 'appartamenti.csv'

run_loop(nome_file_csv, dtype, columns)
