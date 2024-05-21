"""
Įrankiai duomenų parsiuntimui iš https://archyvas.meteo.lt/ kaip CSV ir arba nuskaitymui pandas.DataFrame

Duomenų šaltinis yra Lietuvos hidrometeorologijos tarnyba prie Aplinkos ministerijos (LHMT)
https://archyvas.meteo.lt/ neleidžia duomenų atsisiųsti per nuorodą, nors leidžia naršyklėje, pvz., atvėrus
https://archyvas.meteo.lt/?station=vilniaus-ams&start_date=2023-01-01&end_date=2023-12-31&meteo-form=Rodyti
ir pasirinkus CSV ir paspaudus „Atsisiųsti“: https://archyvas.meteo.lt/f94e79f6-6e1c-4536-91f2-503eedce32aa
Siekiant suderinmumo su čia esančiu kodu, rankiniu būdu parsisiųstąsias rinkmenas reikia išsaugoti pagal schemą
 "{stoties_kodas}_{metai}.csv" (numatytuoju atveju naršyklė siūlo vieną ir tą patį pavadinimą nepaisant stoties
 kodo ir nepaisant pasirinkto laikotarpio). Parsisiųstiems orų duomenims taikoma CC BY-SA 4.0 licencija

(c) 2024 Mindaugas Baranauskas

---

Ši programa yra laisva. Jūs galite ją platinti ir/arba modifikuoti
remdamiesi Free Software Foundation paskelbtomis GNU Bendrosios
Viešosios licencijos sąlygomis: 3 licencijos versija, arba (savo
nuožiūra) bet kuria vėlesne versija.

Ši programa platinama su viltimi, kad ji bus naudinga, bet BE JOKIOS
GARANTIJOS; taip pat nesuteikiama jokia numanoma garantija dėl TINKAMUMO
PARDUOTI ar PANAUDOTI TAM TIKRAM TIKSLU. Daugiau informacijos galite 
rasti pačioje GNU Bendrojoje Viešojoje licencijoje.

Jūs kartu su šia programa turėjote gauti ir GNU Bendrosios Viešosios
licencijos kopiją; jei ne - žr. <https://www.gnu.org/licenses/>.

---

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import os
import re
import json
import datetime
import pandas as pd
from time import sleep
from bs4 import BeautifulSoup
from parsiuntimai import gauti_internetu  # vietinė f-ja parsisuntimams; vietoj to galima naudoti requests


def gauti_visus_orus(metai_nuo=None, metai_iki=None,
                     vietiniai_pavieniai_csv=True, csv_katalogas=None):
    """
    Parsiunčia Lietuvos orų duomenų archyvą iš <https://archyvas.meteo.lt/> ir, jei prašoma,
    kiekvienos stoties kiekvienų metų duomenis atskirai irašo į CSV

    Įvedimo parametrai:
    :param metai_nuo: nuo kurių metų imti duomenis
    :param metai_iki: iki kurių metų imti duomenis
    :param vietiniai_pavieniai_csv: [True|False] įrašyti kiekvienos stoties ir kiekvienų metų duomenis atskirai į CSV
    :param csv_katalogas: katalogas, kur įrašyti CSV, jei vietiniai_pavieniai_csv=True (numatytasis 'data/orai/')
    """

    # Pradiniai kintamieji
    visi_duomenys = []
    stotys = gauti_stotis()  # žodynas su stočių kodais ir pavadinimais
    dabartiniai_metai = datetime.date.today().year
    if not metai_iki:
        metai_iki = dabartiniai_metai
    if not metai_nuo:
        metai_nuo = 2021  # imti 2021 metų, kuriems turime elektros duomenis
    metai_nuo = min(2013, metai_nuo)  # archyvas.meteo.lt turi duomenis tik nuo 2013 m.
    if csv_katalogas is None:
        csv_katalogas = os.path.join('data', 'orai')

    print('\nGaunami duomenys:')
    for stotis in stotys:
        stoties_kodas = stotis['code']
        stoties_pavad = stotis['name']

        for metai in range(metai_nuo, metai_iki + 1):

            vietinis_stoties_csv = os.path.join(csv_katalogas, f'{stoties_kodas}_{metai}.csv')  # CSV rinkmena

            if os.path.exists(vietinis_stoties_csv) and (metai != dabartiniai_metai):
                # Jei yra praeitų metų duomenys - jie nebesikeis ir nebereikia parsisiuntinėti
                print('%s %d m. duomenis greičiausiai jau turite %s - jie nebus parsiunčiami ir jų turinio neskaitome'
                      % (stoties_pavad, metai, vietinis_stoties_csv))

            else:  # (not os.path.exists(vietinis_stoties_csv)) or (metai == dabartiniai_metai) :
                # Visada parsisiųsti šių metų duomenis iš naujo, nes pildosi; taip pat jei dar neturėjome senesnių metų
                print(' Parsiunčiami %s %d m. orai' % (stoties_pavad, metai))
                stoties_duomenys = parsisiųsti_stoties_orus_metinius(stoties_kodas, metai)

                if not stoties_duomenys:  # jei nerado duomenų, t.y. greičiausiai grąžino None arba []
                    print(' - Duomenų gauti nepavyko')
                    sleep(1)  # palaukti sekundę, kad mažiau apkrautų meteo.lt svetainę
                    continue

                if vietiniai_pavieniai_csv:
                    try:
                        pd.DataFrame(stoties_duomenys).to_csv(vietinis_stoties_csv, index=False)
                    except Exception as err:
                        print(f' - Klaida įrašant į {vietinis_stoties_csv}:', err)
                    else:
                        print(' - Sėkmingai įrašyta į', vietinis_stoties_csv)
                sleep(1)  # palaukti sekundę, kad mažiau apkrautų meteo.lt svetainę

                # Kadangi vienos stoties metinius duomenis turime, įtraukiame juos į didįjį duomenų rinkinį
                visi_duomenys.extend(stoties_duomenys)

    if visi_duomenys:
        print('Orų parsisiuntimas baigtas.')
    else:
        print('Nepavyko rasti nei vienos orų stoties duomenų jokių pasirinktu laikoktarpiu.')
        return


def gauti_stotis():
    # grąžina automatinio matavimo stočių kodus ir jų pavadinimus kaip žodyną.
    stotys = []
    stotys_url = 'https://api.meteo.lt/v1/stations'
    stotys_json = gauti_internetu(stotys_url)  # requests.get(stotys_url).text su įvairiais tikrinimais
    if stotys_json:
        stotys_json_dict = json.loads(stotys_json)  # nors visi reikalingi duomenys yra, bet vėliau pertvarkyti
        for stotis in stotys_json_dict:
            stoties_info_lentelei = {
                'code': stotis['code'],
                'name': stotis['name'].replace(' AMS', ''),
                'latitude': stotis['coordinates']['latitude'],
                'longitude': stotis['coordinates']['longitude'],
            }
            stotys.append(stoties_info_lentelei)
    return stotys


def parsisiųsti_stoties_orus_metinius(stotis='vilniaus-ams', metai=2023):
    """
    Parsisiunčia metinius orų duomenis iš <https://archyvas.meteo.lt/>, kur jie saugomi iki paskutinių 10-ties metų,
    ir grąžina žodynų sąrašą.

    Įvedimo parametrai:
      stotis - matavimų stoties kodas (būtinas),
      metai  - metai (tinka nuo 2013) (būtinas)
    Išsamesnį aprašymą rasite prie parsisiųsti_stoties_orus_pavienius funkcijos
    """

    stoties_duomenys = parsisiųsti_stoties_orus_pavienius(stotis=stotis, metai=metai)
    if stoties_duomenys == []:  # bet ne None, todėl negalima supaprastinti iki „not stoties_duomenys“
        # spec. atvejis, kai nepavyksta parsiųsti, pvz.,
        # 2021 Nidos
        # 2020 Panevėžio
        # 2021 Raseinių
        # 2023 Šilutės
        # 2021 Varėnos

        # nepavykus paimti visų metų, imti pamėnesiui
        for mėnuo in range(1, 13):
            stoties_duomenys_mėn = parsisiųsti_stoties_orus_pavienius(stotis=stotis, metai=metai, mėnuo=mėnuo)
            if stoties_duomenys_mėn:
                stoties_duomenys.extend(stoties_duomenys_mėn)
                sleep(1)  # palaukti sekundę, kad mažiau apkrautų meteo.lt svetainę
            elif stoties_duomenys_mėn is None:
                continue
            elif not stoties_duomenys_mėn:  # spec. atvejis sdm==[] (bet ne None), pvz., su
                # 2021-04 Nidos
                # 2020-08 Panevėžio
                # nuo 2021-10 iki 2021-11 Raseinių
                # nuo 2023-09 iki 2023-10 Šilutės
                # 2021-07 Varėnos

                # nepavykus paimti pamėnesiui, imti padieniui
                if mėnuo == 12:
                    pask_mėn_diena = 31  # gruodžio paskutinė mėnesio diena yra 31 d.
                else:
                    pask_mėn_diena = int((datetime.date(metai, mėnuo + 1, 1) - datetime.timedelta(1)).day)
                for diena in range(1, pask_mėn_diena + 1):
                    stoties_duomenys_d = parsisiųsti_stoties_orus_pavienius(stotis, metai, mėnuo, diena)
                    if stoties_duomenys_d:
                        stoties_duomenys.extend(stoties_duomenys_d)
                        sleep(1)  # palaukti sekundę, kad mažiau apkrautų meteo.lt svetainę
                    # Bet vis tiek nepavyksta su:
                    # nuo 2021-04-18 iki 2021-04-19 Nidos
                    # nuo 2020-08-06 iki 2020-08-09 Panevėžio
                    # nuo 2021-10-22 iki 2021-10-23 Raseinių
                    # nuo 2021-11-05 iki 2021-11-07 Raseinių
                    # nuo 2023-09-30 iki 2023-10-01 Šilutės
                    # 2021-07-08, 2021-07-11, 2021-07-12 Varėnos
    return stoties_duomenys


def parsisiųsti_stoties_orus_pavienius(stotis='vilniaus-ams', metai=2023, mėnuo=None, diena=None):
    # Parsisiunčia istorinius orų duomenis iš <https://archyvas.meteo.lt/>, kur jie saugomi iki paskutinių 10-ties metų,
    # ir grąžina žodynų sąrašą.
    #
    # Įvedimo parametrai:
    #   stotis - matavimų stoties kodas (būtinas),
    #   metai  - metai (tinka nuo 2013) (būtinas),
    #   mėnuo ir diena - nebūtini parametrai
    #
    # Automatinio matavimo stotys (kodai ir pavadinimai):
    #     "birzu-ams": "Biržų",
    #     "dotnuvos-ams": "Dotnuvos",
    #     "duksto-ams": "Dūkšto",
    #     "kauno-ams": "Kauno",
    #     "klaipedos-ams": "Klaipėdos",
    #     "kybartu-ams": "Kybartų",
    #     "laukuvos-ams": "Laukuvos",
    #     "lazdiju-ams": "Lazdijų",
    #     "nidos-ams": "Nidos",
    #     "panevezio-ams": "Panevėžio",
    #     "raseiniu-ams": "Raseinių",
    #     "siauliu-ams": "Šiaulių",
    #     "silutes-ams": "Šilutės",
    #     "telsiu-ams": "Telšių",
    #     "ukmerges-ams": "Ukmergės",
    #     "utenos-ams": "Utenos",
    #     "varenos-ams": "Varėnos",
    #     "vilniaus-ams": "Vilniaus"
    # Žr. išsamią informaciją apie stotis JSON formatu: https://api.meteo.lt/v1/stations
    #
    # Raktai žodyne ir jų lietuviški paaiškinimai (remiantis <https://api.meteo.lt/>):
    #   'obs_time_utc': 'atliktų stebėjimų laikas (UTC laiko juosta)',
    #   'station_code': 'stoties kodas',
    #   'air_temperature': 'oro temperatūra, °C',
    #   'feels_like_temperature': 'juntamoji temperatūra, °C',
    #   'wind_speed': 'vėjo greitis, m/s',
    #   'wind_gust': 'vėjo gūsis, m/s. Maksimalus gūsis per valandą',
    #   'wind_direction': 'vėjo kryptis, °. Reikšmės: 0 - iš šiaurės, 180 - iš pietų ir t. t.',
    #   'cloud_cover': 'debesuotumas, %. Reikšmės: 0 - giedra, 100 - debesuota, null - nenustatytas (pvz., dėl rūko)',
    #   'sea_level_pressure': 'slėgis jūros lygyje, hPa',
    #   'relative_humidity': 'santykinis oro drėgnis, %',
    #   'precipitation': 'kritulių kiekis, mm. Kritulių suma per valandą',
    #   'condition_code': 'orų sąlygos, kodas'
    #
    # Galimos orų sąlygų reikšmės:
    #     clear - giedra;
    #     partly-cloudy - mažai debesuota;
    #     variable-cloudiness - nepastoviai debesuota;
    #     cloudy-with-sunny-intervals - debesuota su pragiedruliais;
    #     cloudy - debesuota;
    #     thunder - perkūnija;
    #     isolated-thunderstorms - trumpas lietus su perkūnija;
    #     thunderstorms - lietus su perkūnija;
    #     light-rain - nedidelis lietus;
    #     rain - lietus;
    #     heavy-rain - smarkus lietus;
    #     rain-showers - trumpas lietus;
    #     light-rain-at-times - protarpiais nedidelis lietus;
    #     rain-at-times - protarpiais lietus;
    #     light-sleet - nedidelė šlapdriba;
    #     sleet - šlapdriba;
    #     sleet-at-times - protarpiais šlapdriba;
    #     sleet-showers - trumpa šlapdriba;
    #     freezing-rain - lijundra;
    #     hail - kruša;
    #     light-snow - nedidelis sniegas;
    #     snow - sniegas;
    #     heavy-snow - smarkus sniegas;
    #     snow-showers - trumpas sniegas;
    #     snow-at-times - protarpiais sniegas;
    #     light-snow-at-times - protarpiais nedidelis sniegas;
    #     snowstorm - pūga;
    #     mist - rūkana;
    #     fog - rūkas;
    #     squall - škvalas;
    #     null - oro sąlygos nenustatytos.

    # Laikotarpio suformavimas
    if mėnuo:  # prašomas konkretus mėnuo
        # Data nuo 1 mėnesio dienos, nebent naudotojas nurodė konkrečią
        data_nuo = f'{metai}-{mėnuo:02d}-' + (f'{diena:02d}' if diena else '01')
        # Data iki
        if mėnuo == 12:  # gruodžiui 31 d., nebent naudotojas nurodė konkrečią dieną
            data_iki = f'{metai}-12-' + (f'{diena:02d}' if diena else '31')
        elif diena:  # naudotojo nurodyta diena
            data_iki = f'{metai}-{mėnuo:02d}-{diena:02d}'
        else:  # automatiškai apskaičiuoti paskutinę mėnesio dieną
            data_iki = str(datetime.date(metai, mėnuo + 1, 1) - datetime.timedelta(1))
    else:  # visi metų mėnesiai
        data_nuo = f'{metai}-01-01'
        data_iki = f'{metai}-12-31'

    # URL adreso suformavimas ir parsiuntimas
    url = f'https://archyvas.meteo.lt/?station={stotis}&start_date={data_nuo}&end_date={data_iki}&meteo-form=Rodyti'
    html_turinys = gauti_internetu(url)  # parsisiųsti HTML turinį
    if not html_turinys:  # Nepavykus gauti HTML turinio, kai svetainė nepasiekiama ar nurodyto puslapio nėra
        return None

    # Analizuoti gautą HTML turinį
    soup = BeautifulSoup(html_turinys, 'html.parser')  # inicijuoti HTML turinio nagrinėjimą
    js_turinys = soup.find_all('script')  # išrinkti JavaScript blokus, kiekvienas blokas atskirame sąrašo elemente
    # rasti, JS bloką, kuriame apibrėžtas kintamasis su orų duomenimis
    js_kintamieji = [txt for txt in js_turinys if txt.text.find('var tempChartIntervalResults =') > 0]
    if not js_kintamieji:  # jei nepavyko rasti tinkamo JS bloko
        print(f' - Svetainė archyvas.meteo.lt pasiekiama, bet nepavyko rasti „tempChartIntervalResults“ '
              f'laikotarpiui nuo {data_nuo} iki {data_iki}')
        return []  # grąžinti tuščią sąrašą, kad aukštesnė funkcija žinotų, kad galima bandyti pamėnesiui

    # Ištraukti JavaScript kintamojo tempChartIntervalResults reikšmes su orų duomenimis
    orai_json = re.search(r'var tempChartIntervalResults = (.+?])', js_kintamieji[0].text, re.MULTILINE).group(1)
    try:
        orai = json.loads(orai_json)  # konvertuoti į žodyną. Pastaba: skaičiai išsaugoti kaip tekstas!
    except ValueError:
        print("Netinkamai išgautas JSON")
        return None
    else:
        return orai  # grąžina žodynų sąrašą


def stotys_ir_regionai(csv_rinkmena='data/meteo_stotys_regionuose.csv', tyliai=False):
    """
    Meteorologijos stočių kodai ir regionai, su stočių koordinatėmis.
    Nuskaito jas iš CSV, bet jei jo nėra, tada kuria naudojant gauti_stotis() ir pervadina kai kuriuos regionus
    :param csv_rinkmena: kur ieškoti / saugoti CSV
    :param tyliai: ar rodyti paaiškinimus
    :return: pandas.DataFrame su stulpeliais 'station_code', 'Regionas', 'latitude', 'longitude'
    """

    privalomi_stulpeliai = ['station_code', 'Regionas', 'latitude', 'longitude']  # būtini CSV kintamieji

    if isinstance(csv_rinkmena, str) and os.path.isfile(csv_rinkmena):
        if not tyliai:
            print('Meteorologijos stočių ir regionų atitikmenų sąrašas rastas rinkmenoje', csv_rinkmena)
        try:
            df = pd.read_csv(csv_rinkmena)
        except Exception as err:
            if not tyliai:
                print(' ...tačiau nepavyko nuskaityti reikiamų duomenų:', err)
        else:
            if all([st in df.columns for st in privalomi_stulpeliai]):  # ar CSV turi kiekvieną norimą stulpelį
                return df[privalomi_stulpeliai]
            elif not tyliai:
                print(' ...tačiau trūksta kai kurių kintamųjų.')

    # Jei rinkmenos nebuvo, sukurti
    stotys = gauti_stotis()  # pilna informacija apie stotis, jei pavyko pasiekti internetą
    df = pd.DataFrame(stotys)  # konvertuoti į pandas lentelę
    # Pervadinti kintamuosius:
    df = df.rename(columns={
        'code': 'station_code',  # tokio pavadinimo stulpelyje saugomas stoties identifikatorius meteo archyvo duomenyse
        'name': 'Regionas',  # Savivaldybių pavadinimai dažnai sutampa su stočių pavadinimais, su išimtimis
    })
    # Savivaldybių pavadinimų skirtumai nuo stočių pavadinimų:
    df['Regionas'] = df['Regionas'].replace({
        'Dotnuvos': 'Kėdainių',
        'Dūkšto': 'Ignalinos',
        'Kybartų': 'Vilkaviškio',
        'Laukuvos': 'Šilalės',
        'Nidos': 'Neringos',  # bet šiai savivaldybei/regionui neturime ESO elektros duomenų
        # 'Vilniaus': 'Vilniaus miesto',  # pagal ESO regionus, bet tada 'Vilniaus rajono' liktų be stoties
    })
    # Beje, ESO regionai (savivaldybės) be meteorologijos stočių:
    # ['Akmenės', 'Alytaus', 'Anykščių', 'Druskininkų', 'Gargždų', 'Jonavos', 'Joniškio', 'Jurbarko',
    #  'Kaišiadorių', 'Kelmės', 'Kretingos', 'Kupiškio', 'Kuršėnų', 'Marijampolės', 'Mažeikių',
    #   'Molėtų','Pakruojo', 'Pasvalio', 'Plungės', 'Prienų', 'Radviliškio', 'Rokiškio', 'Skuodo',
    #  'Šakių', 'Šalčininkų', , 'Širvintų', 'Švenčionių', 'Tauragės', 'Trakų', 'Zarasų',

    df = df[privalomi_stulpeliai]  # palikti tik būtinus stulpelius
    if isinstance(csv_rinkmena, str):
        df.to_csv(csv_rinkmena, index=False)  # eksportuoti į CSV naudojimui pakartotinai vėliau
        if not tyliai:
            print('Meteorologijos stočių kodai ir regionai įrašyti į', csv_rinkmena)
    return df
