import os.path
import pandas as pd

def read_if_file_exists(nome_file_csv, dtype, columns):
    if os.path.isfile(nome_file_csv): 
        df_tot = pd.read_csv(nome_file_csv, sep = ';', dtype = dtype)
    else:
        df_tot= pd.DataFrame(columns=columns)
    return df_tot

