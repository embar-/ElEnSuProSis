"""
Bendrieji įrankiai parsisiuntimams iš interneto
"""

import os
import platform
import requests
from bs4 import BeautifulSoup  # reikalingas beautifulsoup4 paketas
from urllib.parse import unquote  # url adresuose esančių simbolių kodų pakeitimui į įprastus


def gauti_internetu(url, atsakymo_tipas='content', detaliai=False):
    """
    Pagal pateiktą URL adresą grąžina internetinio puslapio turinį (HTML kodą) kaip kintamąjį (neįrašo į diską)
    """
    # pvz., gali parsiųsti
    # https://archyvas.meteo.lt/?station=vilniaus-ams&start_date=2014-01-01&end_date=2014-12-31&meteo-form=Rodyti

    # Naršylės imitavimas priklausomai nuo operacinės sistemos
    operacine_sist = platform.system()  # Linux, Windows, Darwin (Mac)
    if operacine_sist == 'Windows':
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0'}
    elif operacine_sist == 'Linux':
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0'}
    elif operacine_sist == 'Darwin':  # MAC OS
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:115.0) Gecko/20100101 Firefox/115.0'}
    else:
        headers = None

    # Pats puslapio parsisiuntimas
    try:
        atsakas = requests.get(url, headers=headers, stream=True)  # stream dėl didesnių rinkmenų - srautas dalinamas
    except requests.exceptions.ConnectionError:
        print("Nepavyko pasiekti interneto. Patikrinkite ryšį.")
        return None

    # Atsakymo tikrinimas
    if atsakas.status_code == 200:
        if detaliai:
            print(f' - Pavyko pasiekti {url}')
        if atsakymo_tipas in ['text', 'txt', 'tekstas']:
            return atsakas.text
        if atsakymo_tipas in ['content', 'turinys']:
            return atsakas.content
        else:
            return atsakas
    else:
        print(f' - Nepavyko pasiekti {url}: {atsakas.status_code}')
        if detaliai:
            print(BeautifulSoup(atsakas.text, 'html.parser').text.strip())
        return None


def parsisiųsti_rinkmeną(url, vietinis_kelias=None, detaliai=True):
    """
    Parsisiųsti dokumentą iš interneto ir jį išsaugoti diske
    :param url:
    :param vietinis_kelias:
    :param detaliai:
    :return: Grąžina pilną kelią, kur dokumentas įrašytas
    """

    try:
        vardas = rinkmenos_vardas_pagal_url(url)  # parsisiunčiamos rinkmenos vardas

        # jei nenurodytas, atspėti rikmenos vardą saugojimui pagal url
        if not vietinis_kelias:  # naudotojas nenurodė kaip įrašyti, tad pavadinimą parinkti automatiškai
            vietinis_kelias = vardas

        # sukurti katalogą, jei nėra
        katalogas = os.path.abspath(os.path.dirname(vietinis_kelias))
        if katalogas and not os.path.exists(katalogas):  # jei katalogo nėra
            os.makedirs(katalogas)  # sukurti katalogą

        if os.path.isdir(vietinis_kelias):  # kelias yra tik katalogas
            vietinis_kelias = os.path.join(vietinis_kelias, vardas)  # prie kelio pridėti pavadinimą

        # patikslinti kelią saugojimui
        vietinis_kelias = os.path.abspath(vietinis_kelias)

        # parsisiųti dokumento turinį
        turinys = gauti_internetu(url, atsakymo_tipas='content')
        if not turinys:  # Jei nepavyko parsisiųsti
            return None

        # įrašyti dokumentą
        with open(vietinis_kelias, 'wb') as rinkmena:
            rinkmena.write(turinys)
        if detaliai:
            print(' Sėkmingai parsiųsta rinkmena', vardas, 'ir įrašyta į\n ', vietinis_kelias)
        return vietinis_kelias  # grąžinti kelią, kur įrašyta

    except Exception as err:
        if detaliai:
            print('   Klaida parsisiunčiant „%s“:\n   %s' % (url, err))
        return None


def išrinkti_nuorodas_iš_puslapio(puslapio_url, lentelės_požymiai=None, nuorodos_tekstas=None):
    """
    Iš duombazės aprašo puslapio, kuriame yra lentelė su nuorodomis į duomenis, išrenka tas nuorodas

    Įvedimo parametrai:
      puslapio_url      - duombazės aprašo puslapis su nuorodų lentele
      lentelės_požymiai - lentelės unikalios ypatybės, kurios padeda pasirinkti reikiamą lentelę, ypač jei jų kelios
      nuorodos_tekstas  - tekstas, kuris yra tarp <a> ir </a> HTML kodo dalių
    """

    # Patikrinti įvedimo kintamuosius
    if not (type(puslapio_url) is str and '://' in puslapio_url):  # nėra (teksto ir protokolo)?
        print('Pirmasis argumentas turi būti puslapio URL. Netinka pateiktasis: %s' % puslapio_url)
        return []
    if not (type(nuorodos_tekstas) in [str, type(None)]):
        print('Parametras „nuorodos_tekstas“ yra papildomas kriterijus nuorodoms atrinkti. Jis turi būti tekstinis')
        return []

    # Parsisiųsti HTML puslapį
    html_puslapio_turinys = gauti_internetu(puslapio_url, atsakymo_tipas='text')  # Gauti HTML kodą kaip tekstą
    if not html_puslapio_turinys:  # jei nepavyko parsiųsti HTML puslapio
        return []  # grąžinti, tuščią sąrašą - jokių nuorodų

    # HTML puslapyje rasti lentelę
    soup = BeautifulSoup(html_puslapio_turinys, 'html.parser')  # inicijuoti html puslapio nagrinėjimą
    lentele = soup.find('table', attrs=lentelės_požymiai)  # ieškoti lentelės
    if not lentele:  # jei lentelės rasti nepavyko
        return []

    # Darbas su lentelės nuorodomis
    a_blokai = lentele.find_all('a')  # surasti visus nuorodų blokus
    if nuorodos_tekstas in [None, '']:  # naudotojas nenurodė jokios nuorodų atrankos filtro
        nuorodos = [blokas['href'] for blokas in a_blokai]  # visos nuorodos (href=), be jokios atrankos
    else:  # naudotojas nurodė nuorodų atrankos filtrą
        nuorodos = [blokas['href'] for blokas in a_blokai if blokas.text.strip() == nuorodos_tekstas]  # su atranka
    protokolas_ir_domenas = '/'.join(puslapio_url.split('/')[:3])  # prireiks žemiau, jei nuoroda neturės jų
    for i, nuoroda in enumerate(nuorodos):
        if '://' not in nuoroda:  # jei nuoroda neturi protokolo ir domeno
            if nuoroda[0] == '/':  # nuoroda prasideda /
                nuorodos[i] = protokolas_ir_domenas + nuoroda  # pridėti protokolą ir domeną pagal pirminį puslapį
            else:
                nuorodos[i] = '/'.join(puslapio_url.split('/')[:-1]) + '/' + nuoroda  # pakeisti pradinio puslapio galą
    return nuorodos


def rinkmenos_vardas_pagal_url(url):
    url_dalys = [dalis for dalis in (url + '/').split('/') if dalis]  # netuščios dalys URL adrese
    return unquote(url_dalys[-1])
