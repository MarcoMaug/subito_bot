import requests
import pandas as pd
import time

import traceback
from bs4 import BeautifulSoup
import utils
import utils_subito

logger = utils.set_log('./subito_affitti.log', 'info', 'subito_affitti')


def extract_data_subito(soup):
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


def extract_data_idealista(soup):
    titolo_list=[]
    town_list=[]
    prezzo_list=[]
    sito_list=[]
    
    # Estrazione dei link degli annunci
    siti = soup.find_all("a", class_="item-link")
    for sito in siti:
        href = sito['href']
        link_completo = f"https://www.idealista.it{href}"
        sito_list.append(link_completo)
    
    # Estrazione dei titoli, città e prezzi
    annunci = soup.find_all("a", class_="item-link")
    for annuncio in annunci:
        # Estrai il titolo
        titolo = annuncio['title'].strip()
        if titolo.lower() in ['smart']:
            continue
        else:
            # Estrai la città e altre informazioni rilevanti dal testo
            citta = titolo.split(",")[-1].strip()  # Estrai la città dal titolo
            titolo_list.append(titolo)
            town_list.append(citta)
    
    # Estrazione dei prezzi
    prezzi = soup.find_all("span", class_="item-price")
    for prezzo_elem in prezzi:
        prezzo = prezzo_elem.text.strip().split("€")[0].replace(".", "").replace("€/mese", "").strip()
        prezzo = int(prezzo)  # Converti il prezzo in intero
        prezzo_list.append(prezzo)
    
    return titolo_list, town_list, prezzo_list, sito_list


def extract_data_immobiliare(json_data):
    titolo_list=[]
    town_list=[]
    prezzo_list=[]
    sito_list=[]
    # Estrazione dei dati dal JSON
    for result in json_data['results']:
        # Estrai il titolo
        titolo = result['realEstate']['title']
        titolo_list.append(titolo)
        
        # Estrai la città
        town = result['realEstate']['location']['city']
        town_list.append(town)
        
        # Estrai il prezzo
        prezzo = result['realEstate']['price']['value']
        prezzo_list.append(prezzo)
        
        # Estrai il link all'annuncio
        sito = result['seo']['url']
        sito_list.append(sito)
    return titolo_list, town_list, prezzo_list, sito_list


    
def add_data(nome_file_csv, dtype, website, url, columns):
    try:
        df_tot = utils_subito.read_if_file_exists(nome_file_csv,dtype, columns)
        df_tot['nuovo']=0
        if website == 'idealista':
            headers = {
                'authority': 'www.idealista.it',
                'method': 'GET',
                'path': url.split("www.idealista.it")[1],
                'scheme': 'https',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'max-age=0',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
            page = requests.get(url, headers = headers)
            soup = BeautifulSoup(page.content, "html.parser")
        elif website == 'immobiliare':
            headers = {
                'authority': "www.immobiliare.it",
                'method': 'GET',
                "path": "/api-next/search-list/real-estates/?vrt=45.481202%2C9.093933%3B45.487464%2C9.275208%3B45.606786%2C9.275208%3B45.662991%2C9.220276%3B45.671153%2C9.130325%3B45.644262%2C9.054108%3B45.599576%2C9.002609%3B45.481202%2C9.093933&idContratto=2&idCategoria=1&prezzoMinimo=500&prezzoMassimo=600&criterio=data&ordine=desc&_lang=it&minLat=42.201066&maxLat=48.724501&minLng=9.013057&maxLng=9.319301&pag=1&paramsCount=13&path=%2Fsearch-list%2F",
                'scheme': 'https',
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
            page = requests.get(url, headers = headers)
        else:
            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser")
        if website == 'subito':
            titolo_list, town_list, prezzo_list, sito_list = extract_data_subito(soup)
        elif website == 'idealista':
            titolo_list, town_list, prezzo_list, sito_list = extract_data_idealista(soup)
        elif website == 'immobiliare':
            titolo_list, town_list, prezzo_list, sito_list = extract_data_immobiliare(page)
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
    logger.info("loop eseguito per %s", website)

def run_loop(nome_file_csv, dtype, websites, columns, seconds_to_sleep=300):
    while (1):
        try:
            for key in websites.keys():
                add_data(nome_file_csv, dtype, key, websites[key], columns)
        except Exception:
            traceback.print_exc()
        time.sleep(seconds_to_sleep)
        logger.info("fine tutti i loop websites:%s", str(websites))

        
    



dtype = {'name': str,'citta': str,
         'prezzo': 'float64',
         'data':'Int64',
         'sito':str,
        }
columns = ['nome','citta','prezzo','sito','nuovo']
json_data = utils.read_json_file('./config_template.json')
token, chat_id =  utils.read_account_info(json_data)
# Ottieni price_min e price_max
price_min = json_data['price_min']
price_max = json_data['price_max']

url = f'https://www.subito.it/annunci-locali/affitto/appartamenti/?q=appartamento&rad=7500&lat=45.57122&lon=9.15921&ps={price_min}&pe={price_max}'
url_idealista = f'https://www.idealista.it/aree/affitto-case/con-prezzo_{price_max},prezzo-min_{price_min}/?ordine=pubblicazione-desc&shape=%28%28us%7EtGki%7Cu%40s%7DTa%7B%40%7EAmds%40tjVnr%40vwH%60dCdx%40r%7BZ_aLhkS%29%29'
url_immobiliare = f'https://www.immobiliare.it/search-list/?idContratto=2&idCategoria=1&prezzoMinimo={price_min}&prezzoMassimo={price_max}&criterio=data&ordine=desc&__lang=it&vrt=45.481202%2C9.093933%3B45.487464%2C9.275208%3B45.606786%2C9.275208%3B45.662991%2C9.220276%3B45.671153%2C9.130325%3B45.644262%2C9.054108%3B45.599576%2C9.002609%3B45.481202%2C9.093933&pag=1&mapCenter=45.557343%2C9.165836&zoom=11'
websites = {
            "subito":url,
            "idealista":url_idealista
            #"immobiliare": url_immobiliare
            }
nome_file_csv = 'appartamenti.csv'

run_loop(nome_file_csv, dtype, websites, columns)
