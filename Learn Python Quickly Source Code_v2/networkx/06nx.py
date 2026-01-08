# Median Time: 10 seconds  
 
import gzip
import shutil
import requests
 
url = 'https://snap.stanford.edu/data/cit-Patents.txt.gz'
name = 'cit-Patents.txt'
 
# Download gz
response = requests.get(url, stream=True)
response.raise_for_status()
 
# Stream gz data & write to text file
with response.raw as r, gzip.open(r, 'rb') as f_in, open(name, 'wb') as f_out:
    shutil.copyfileobj(f_in, f_out)