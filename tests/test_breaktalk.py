import requests
from bs4 import BeautifulSoup

url = 'https://breadtalkvietnam.com/tiramisu-c/'  

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://breadtalkvietnam.com/',
}

res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.text, 'html.parser')

price_tag = soup.select_one('p.price span.woocommerce-Price-amount bdi')
print('Giá lấy được:', price_tag.text if price_tag else 'Không tìm thấy')
