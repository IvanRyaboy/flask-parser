from typing import List, Dict

import requests
from bs4 import BeautifulSoup
import fake_useragent


def parse_all_apartments_ids_from_realt() -> List[Dict]:
    session = requests.Session()
    url = "https://realt.by/belarus/sale/flats/?page=1&sortType=createdAt"
    headers = {'user-agent': fake_useragent.UserAgent().random}

    response = session.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')

    block = soup.find('div', class_="t-0 l-0 absolute w-full")
    if not block:
        return []

    apartment_ids = []

    apartments = block.find_all('div', attrs={'data-index': True})

    for apt in apartments:
        id_span = apt.find('span', class_='relative z-[2]')
        apt_tag = apt.find('a', class_='z-1 absolute top-0 left-0 w-full h-full cursor-pointer')
        apt_link = 'https://realt.by' + apt_tag.get('href') if apt_tag else None
        if id_span:
            text = id_span.get_text(strip=True)
            apt_id = text[2:].strip()
            apartment_ids.append({'_id': apt_id, 'link': apt_link, 'state': 'first'})

    return apartment_ids


def parse_apartment_data_from_realt(url: str):
    session = requests.Session()
    headers = {'user-agent': fake_useragent.UserAgent().random}

    response = session.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')

    title = soup.find('h1', class_='order-1 mb-0.5 md:-order-2 md:mb-4 block w-full !inline-block lg:text-h1Lg text-h1 font-raleway font-bold flex items-center').text
    price = soup.find('h2', class_='!inline-block mr-1 lg:text-h2Lg text-h2 font-raleway font-bold flex items-center').text
    title = title.replace('\xa0', ' ').strip()
    price = price.replace('\xa0', ' ').strip()
    data = {'title': title, 'price': price}

    for li in soup.select('ul.w-full.-my-1 > li'):
        key = li.select_one('span.text-basic').get_text(strip=True)
        divs = li.find_all('div', class_='w-1/2')
        if len(divs) >= 2:
            value_p = divs[1].find('p')
            value = value_p.get_text(strip=True) if value_p else None
            if value is None:
                value_p = divs[1].find('a')
                value = value_p.get_text(strip=True) if value_p else None
                value = value.replace('\xa0', ' ').strip()
        else:
            value = None
        data[key] = value

    data['state'] = 'second'
    data['link'] = url
    return data


if __name__ == "__main__":
    data = parse_apartment_data_from_realt("https://realt.by/brest-region/sale-flats/object/3824111/")
    print(data)
