import requests
import pandas as pd
import time
import json
import traceback
from bs4 import BeautifulSoup
import os.path
import logging

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

logging.basicConfig(filename='subito_affitti.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')




json_data = read_json_file('./config.json')
token=json_data["token"]
chat_id=json_data["chat_id"]




url = f'https://www.subito.it/annunci-locali/affitto/appartamenti/?q=appartamento&rad=7500&lat=45.57122&lon=9.15921&ps={json_data["price_min"]}&pe={json_data["price_max"]}'
nome_file_csv = 'appartamenti.csv'



def send_message(row, token, chat_id):
    message = row['nome'] + ', ' + str(row['prezzo']) + ' euro, ' + str(row['citta']) + ' ' + row['sito']
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url).json()
    return 1

while (1):
    try:
        if os.path.isfile(nome_file_csv): 
            df_tot = pd.read_csv(nome_file_csv, sep = ';', dtype = {'name': str,'citta': str,
                                                        'prezzo': 'float64',
                                                            'data':'Int64',
                                                            'sito':str,
                                                            })
        else:
            df_tot= pd.DataFrame(columns=['nome','citta','prezzo','sito','nuovo'])
        
        df_tot['nuovo']=0
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        annunci = soup.find_all("div", class_='BigCard-module_upper-data-group__H2CEM')
        
        titolo_list=[]
        town_list=[]
        prezzo_list=[]
        sito_list=[]
    except Exception as e:
        logging.error(e)
        time.sleep(60*5)
    try:
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
                        print(elem)
                        prezzo = int(elem.split('€')[0].replace(".", ""))
                prezzo_list.append(prezzo)
    except Exception as e:
        logging.error(e)
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
        df_send.apply(lambda x: send_message(x, token, chat_id), axis = 1)

        df_tot = df_tot.drop(columns=['nuovo'])
        df_tot.to_csv(nome_file_csv, sep=';',index=False)
    except Exception:
        traceback.print_exc()
        '''
        print("secondo except")
        print(len(titolo_list))
        print(len(town_list))
        print(len(prezzo_list))
        print(len(sito_list))
        print(titolo_list)
        '''
    logging.info("loop eseguito")
    time.sleep(60)
