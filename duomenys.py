"""
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
import datetime
import re  # reguliarieji reiškiniai
import pandas as pd
# papildomai reikalingas openpyxl norint per pandas importuoti Excel XLSX (naujesnio formato)
# papildomai reikalingas xlrd >= 2.0.1 norint per pandas importuoti Excel XLS (senesnio formato)
from time import sleep
from abc import ABC, abstractmethod  # abstrakčioms klasėms kurti
from sklearn.preprocessing import StandardScaler  # duomenų transformacijoms, standartizavimui; reikalingas scikit-learn
import meteo_lt  # vietinė, skirta gauti duomenis iš https://archyvas.meteo.lt/
from parsiuntimai import parsisiųsti_rinkmeną, rinkmenos_vardas_pagal_url, išrinkti_nuorodas_iš_puslapio


"""
Dvi klasių rūšys:
- Rinkinys - apima to pačio tipo duomenis (rinkmenas), pvz., poros metų laikotarpio elektros duomenys
- Lentelė  - viena duomenų rinkinio dalis (rinkmena), pvz., vieno mėnesio elektros duomenys, vieno miesto metų orai
Vienas Rinkinys gali turėti vieną ar kelias Lenteles: elektros ir orų duomenis parsisiunčiami lentelėmis pagal laiką.
Tokia struktūra padeda virtualiai turėti ir apžvelgti duomenis jų dar visų neparsisiuntus, įkelti juos pagal poreikį

Atsargiai:
reikia pataisyti 2021_03_buitis.csv nesistemingai naudojamą dešimtainį skirtuką: 
didelėje dokumento dalyje naudojamas kablelis (nuo Akmenės iki Varėnos), bet pabaigoje naudojamas taškas
(Vilniaus miesto, Vilniaus rajono, Zarasų, Šakių, Šalčininkų, Šiaulių, Šilalės, Šilutės, Širvintų, Švenčionių) 
"""


class Lentelė:
    # Viena lentelė paprastai atitinka vieną pradinę rinkmeną trumpam laikotarpiui

    def __init__(self, lentelės_vieta, tipas, šaltinis=None, licencija=None):
        """
        Pagrindinės bendros lentelių savybės:
        :param lentelės_vieta: URL arba vietinis rinkmenos kelias
        :param tipas: atitinka Rinkinio klasės rinkinio_tipas savybę
        """
        self.lentelės_vieta = str(
            lentelės_vieta)  # URL arba vietinis rinkmenos kelias; parsisiuntus keičiamas į vietinį
        self.tipas = str(tipas)  # atitinka Rinkinio klasės rinkinio_tipas savybę: 'elektra', 'orai', 'gyventojai'
        if šaltinis:
            self.šaltinis = str(šaltinis)
        if licencija:
            self.licencija = str(licencija)

        # Išvestinės savybės:
        # Vardas be kelio
        if tikrinti_ar_vietinė(self.lentelės_vieta):  # ar vietinė?
            self.vardas = os.path.basename(lentelės_vieta)  # priklausomai nuo operacinės sistemos
        else:
            self.vardas = rinkmenos_vardas_pagal_url(lentelės_vieta)  # nuotolinė: nagrinėti kaip url
        self.formatas = self.vardas.split('.')[-1].lower()  # pvz., 'csv', 'xls', 'xlsx'
        self.laikotarpis = self.spėti_laikotarpį()

    def pakeisti_vietine(self, nauja_vieta=None, ar_išsamiai=True):
        """
        Jei buvo nuotolinė vieta, o vėliau ji rasta esanti vietoje arba parsisiųsta,
        naudotojas gali pasikeisti lentelės vietą, tačiau tik tikrą vietinę.
        Tinka elektros ir gyventojų duomenims, bet netinka orų duomenims - LentelėOrams klasėse metodas perrašytas)
        :param nauja_vieta: vietinė rinkmena
        :param ar_išsamiai: [True|False] ar rodyti paaiškinimus
        """

        # Jei nenurodyta nauja vieta, o senoji yra nuotolinė
        if (nauja_vieta is None) and not tikrinti_ar_vietinė(self.lentelės_vieta):
            nauja_vieta = self.vardas

        if not ((type(nauja_vieta) is str) and tikrinti_ar_vietinė(nauja_vieta)):  # jei nauja nėra (tekstas ar vietinė)
            print('Lentelės kelią galite pakeisti tik į vietinį. Nurodykite naują vietą kaip tekstinį kelią.')
            return False

        if os.path.isdir(nauja_vieta):  # jei nurodytas katalogas vietoj tikslaus rinkmenos kelio su jos pavadinimu
            nauja_vieta = os.path.join(nauja_vieta, self.vardas)  # prie kelio pridėti vardą

        if self.lentelės_vieta == nauja_vieta:  # jei nauja ir sena vieta sutampa
            if ar_išsamiai:
                print('Nauja ir sena vieta sutampa:', self.lentelės_vieta)
            return False  # nieko daugiau nedaryti

        if os.path.isfile(nauja_vieta):  # jei rinkmena nauju keliu jau yra
            if ar_išsamiai:
                print('Lentelės vieta keičiama iš %s į jau esamą %s' % (self.lentelės_vieta, nauja_vieta))
            self.lentelės_vieta = nauja_vieta  # pakeisti lentelės vietą metaduomenyse
            return True
        else:
            # parsisiųsti ir atnaujinti kintamąjį
            nauja_vieta = parsisiųsti_rinkmeną(self.lentelės_vieta, nauja_vieta, detaliai=False)
            if nauja_vieta:
                if ar_išsamiai:
                    print('Lentelės vieta keičiama iš %s į naujai parsiųstą %s' % (self.lentelės_vieta, nauja_vieta))
                self.lentelės_vieta = nauja_vieta  # pakeisti lentelės vietą metaduomenyse
            elif ar_išsamiai:
                print('Negalima pakeisti %s vietos į %s, nes jos nėra' % (self.lentelės_vieta, nauja_vieta))
                return False

    def nuskaityti(self):
        """
        Nuskaityti CSV arba Excel rinkmeną.
        Tinka elektros ir gyventojų duomenims, bet netinka orų duomenims - LentelėOrams klasėse metodas perrašytas).
        :return: grąžinti kaip pandas.DataFrame()
        """
        if self.formatas in ['xls', 'xlsx']:  # Jei rinkmenos galūnė yra XLS arba XLSX
            return pd_nuskaityti_excel(self.lentelės_vieta, 2)  # nuskaityti su pandas, bet per tarpinę f-ją
        elif self.formatas == 'csv':  # Jei rinkmenos galūnė yra CSV
            return pd_nuskaityti_csv(self.lentelės_vieta)  # nuskaityti su pandas, bet per tarpinę f-ją dėl parametrų
        else:
            print(f'Nežinau, kaip nuskaityti {self.formatas.upper()} formato rinkmeną {self.lentelės_vieta}')
            return None

    def spėti_laikotarpį(self, ar_su_mėnesiu=None):
        """Atspėti laikotarpį pagal vardą
        Gali praversti pasirenkant laikotarį prieš rinkmenos parsiuntimą ir jos tikrojo turinio peržiūrėjimą

        :param ar_su_mėnesiu: laikotarpio tipas:
          None  = parinkti automatiškai
          False = metai       - tinka visiems duomenims (tipams: elektra, orai, gyventojai)
          True  = metai.mėnuo - skirta elektros duomenims, bet tam tikrais atvejais gali būti ir orams

        :return: metai arba metai.mėnuo; pvz.
            2022 yra metai
            2024.0 yra 2024 m. sausis,
            2023.5 yra 2023 m. birželis
        """

        if ar_su_mėnesiu is None:  # neapibrėžta?
            ar_su_mėnesiu = self.tipas == 'elektra'  # parinkti pagal rinkmenos tipą

        if ar_su_mėnesiu:
            kodas = atrinkti_skaitmenis(self.vardas, 6)  # 4 metų skaitmenys ir 2 mėnesio skaitmenys
        else:
            kodas = atrinkti_skaitmenis(self.vardas, 4)  # 4 mskaitmenys, nes tikimasi tik metų

        # nors prašėme konkretaus skaitmenų skaičiaus, bet atrinkti_skaitmenis f-ja galėjo grąžinti ir mažiau
        if len(kodas) > 4:
            return int(kodas[0:4]) + (int(kodas[4:6]) - 1) / 12  # metai ir mėnuo, pvz. 2023.5 bus 2023 m. birželis
        elif kodas:
            return int(kodas)
        else:
            # aiškinamojo klaidos pranešimo neberašyti, nes įspėjimą pateikia f-ja atrinkti_skaitmenis
            return None

    def info(self, glaustas=False):
        """
        Informacija apie lentelę:
        :param glaustas:
            True  - aprašą pateikti vienoje eilutėje,
            False - aprašą pateikti keloise eilutėse (numatyta)
        """

        # Laikotarpis kaip tekstas
        if type(self.laikotarpis) is float:  # jei trupmeninis skaičius: metai-mėnuo,
            laikotarpis_txt = (str(int(self.laikotarpis)) + '-' +  # metai
                               f'%02d' % round((self.laikotarpis - int(self.laikotarpis)) * 12 + 1))  # mėnuo, pvz., 06
        else:  # turėtų būti sveikasis skaičius
            laikotarpis_txt = str(self.laikotarpis)  # metai

        # Informacijos pateikimas
        if glaustas:
            print(f'Lentelė: {self.tipas} {laikotarpis_txt} <{self.lentelės_vieta}>')
        else:
            print(
                f'Lentelė:\n'
                f' vieta: {self.lentelės_vieta}\n'
                f' tipas: {self.tipas}\n'
                f' laikotarpis: {laikotarpis_txt}'
            )
            for raktas in ['šaltinis', 'licencija']:  # nebūtinos self savybės
                if hasattr(self, raktas):  # jei savybę turi
                    print(f' {raktas}: {self.__getattribute__(raktas)}')  # parašyti jos reikšmę


class LentelėOrams(Lentelė):
    def __init__(self, lentelės_vieta, meteo_stoties_kodas=None, laikotarpis=None,
                 šaltinis='LHMT', licencija='CC BY-SA 4.0'):
        super().__init__(lentelės_vieta, 'orai', šaltinis=šaltinis, licencija=licencija)
        if meteo_stoties_kodas is not None:
            self.stoties_kodas = str(meteo_stoties_kodas)
        else:
            try:  # bandyti spėti stoties kodą, nors greičiausiai to ir neprireiks
                self.stoties_kodas = re.search(r'([a-z]+-ams)', self.vardas).group(1)  # ieško žodžio ir „-ams“
            except AttributeError:
                print(f'Nepavyko atspėti stoties kodo iš vardo „{self.vardas}“.'
                      f'Tikėtasi žodžio mažosiomis lotyniškomis raidėmis su prierašu „-ams“, pvz., „vilniaus-ams“')
                self.stoties_kodas = ''

        if not (laikotarpis is None):
            self.laikotarpis = laikotarpis  # nors laikotarpis atspėtas pagal vardą, bet galima pakeisti. Reikia metų

    def nuskaityti(self):
        """
        Nuskaityti CSV rinkmeną arba parsisiųsti duomenis iš interneto neįrašant į diską
        :return: grąžinti kaip pandas.DataFrame()
        """
        if os.path.isfile(self.lentelės_vieta):
            return pd.read_csv(self.lentelės_vieta)
        else:
            orai_json = meteo_lt.parsisiųsti_stoties_orus_metinius(self.stoties_kodas, self.laikotarpis)  # žodynai
            return pd.DataFrame(orai_json)

    def pakeisti_vietine(self, nauja_vieta=None, ar_išsamiai=True):
        """
        Jei vietinės rinkmnos nėra, ji sukuriama parsisiuntus duomenis iš interneto
        naudotojas gali pasikeisti lentelės vietą, tačiau tik tikrą vietinę
        :param nauja_vieta: čia nenaudojamas, bet yra tik dėl suderinumo su tėvine klase
        :param ar_išsamiai: [True|False] ar rodyti paaiškinimus
        """
        if not os.path.isfile(self.lentelės_vieta):  # jei vietinės rinkmenos dar nėra
            df = self.nuskaityti()  # gauti pačios lentelės turinį
            if len(df):  # jei lentelė nėra tuščia
                kelias = os.path.dirname(os.path.abspath(self.lentelės_vieta))  # rasti katalogą
                if not os.path.isdir(kelias):  # jeigu katalogo nėra
                    os.makedirs(kelias)  # sukurti katalogą
                df.to_csv(self.lentelės_vieta, index=False)  # įrašyti į CSV, nepridedant indeksavimo stulpelio
                if ar_išsamiai:
                    print('Orų lentelė parsiųsta į %s' % self.lentelės_vieta)


class Rinkinys(ABC):  # abstrakti klasė, kurios medodų pavadinimai bendri tarp skirtingų duomenų tipų rinkinių
    """"
    Tai abstrakti klasė. Jūs negalite jos iškviesti tiesiogiai ir naudoti. Verčiau sukurkite klasę pagal rinkinio tipą:
    - RinkinysElektrai()    - elektros energijos suvartojimas,
    - RinkinysOrams()       - meteorologiniai stebėjimai,
    - RinkinysGyventojams() - demografiniai duomenys - gyventojų skaičius ir pasiskirstymas pagal amžių
    """

    def __init__(self, rinkinio_tipas='bendras',
                 metai_nuo=None, metai_iki=None,  # laikotarpis
                 rinkinio_url=None, pilnas_pavadinimas='',
                 katalogas_saugojimui='data', ar_saugoti_paskiras_rinkmenas=True
                 ):
        # Inicijuoti duomenų struktūrą ir bendras rinkinių savybes

        # Pagrindiniai kintamieji
        palaikomi_rinkiniai = ['elektra', 'orai', 'gyventojai']
        if not (rinkinio_tipas in palaikomi_rinkiniai):
            print('Netinkamai nurodytas rinkinio tipas. Tinka tipai:', palaikomi_rinkiniai)
            print('Tipas turėtų būti priskirtas per vaikinę klasę. Tebūnie dabar tai „bendras“ tipas.')
            rinkinio_tipas = 'bendras'
        self.rinkinio_tipas = str(rinkinio_tipas.lower())  # 'bendras', 'elektra', 'orai' arba 'gyventojai'
        self.rinkinys = self.rinkinio_tipas  # galės būti naudojamas kaip vardas arba pakatalogis
        self.pilnas_pavadinimas = pilnas_pavadinimas  # pilnas pavadinimas ar komentaras
        self.rinkinio_url = rinkinio_url  # HTML puslapis, kuriame yra lentele su nuorodomis į CSV, XLS ir pan rinkmenas

        # laikotarpis analizei
        if type(metai_nuo) in [int, float]:  # atskiri metai „nuo“ ir „iki“
            if type(metai_iki) in [int, float]:  # ar skaičiai
                if metai_iki < metai_nuo:
                    print(f'Laikotarpio pabaiga vėlesnė už pradžią. Apverčiama.')
                    metai_nuo, metai_iki = metai_iki, metai_nuo
            else:
                metai_iki = metai_nuo
            self.metai = list(range(int(metai_nuo), int(metai_iki) + 1))
        elif isinstance(metai_nuo, list) and len(metai_nuo) > 0 and metai_iki is None:  # priimti pateikus metų sąrašą
            if all(isinstance(m, int) for m in metai_nuo):
                self.metai = sorted(set(metai_nuo))
            else:
                print('Įspėjimas: pasirinktas laikotarpis turėjo būti metai (skaičius) arba jų sąrašas, tad ignoruojam')
                self.metai = None
        else:
            self.metai = None

        # Pagrindinių duomenų saugojimas
        if not katalogas_saugojimui:  # nurodytas tuščias katalogas
            self.katalogas_saugojimui = '.'  # darbinis katalogas
        else:
            self.katalogas_saugojimui = str(katalogas_saugojimui)  # konvertuoti į tekstą, jei, pvz., būtų skaičius
        if not os.path.isdir(self.katalogas_saugojimui):  # jeigu katalogo nėra
            os.makedirs(self.katalogas_saugojimui)  # sukurti katalogą
        self.rinkinio_rinkmena = os.path.join(
            self.katalogas_saugojimui,  # katalogas ir rinkmena; prie pastarosios prirašyti laikotarpį, jei nurodytas
            self.rinkinys + ('_' + self.metai_tekstu() if self.metai else '') + '.csv'
        )
        self.privalomi_stulpeliai_sutvarkytiems = []  # pagal juos būtų galimybė patikrinti, ar jau sutvarkyti
        self.privalomi_stulpeliai_nesutvarkytiems = []  # pagal juos būtų galimybė patikrinti, duomenys pirminiai
        self.ar_duomenys_sutvarkyti = False  # Numatytuoju atveju žymima, kad duomenys dar nesutvarkyti

        # Ar parsiųstas saugoti duomenų gabaliukų rinkmenas pakatalogyje (ne tik sujungtas pagrindiniame kataloge)?
        # Parinktis naudinga, nes kas kelis mėnesius duombazė papildoma - nereikės vėl siųstis visko, tik papildyti
        self.ar_saugoti_paskiras_rinkmenas = bool(ar_saugoti_paskiras_rinkmenas)
        if self.ar_saugoti_paskiras_rinkmenas:
            self.katalogas_paskiroms_rinkmenoms = os.path.join(self.katalogas_saugojimui, self.rinkinys)
        else:
            self.katalogas_paskiroms_rinkmenoms = None

        # Kiti kintamieji, kuriuos turėtų turėti rinkiniai
        self.formatai = ['csv', 'xlsx', 'xls']  # palaikomi rinkmenų formatai ieškant vietinių rinkmenų
        self.html_lentelės_požymiai = None  # BeautifulSoup naudos duombazės apraše ieškant sąrašo su duomenų nuorodomis
        self.html_nuorodos_tekstas = None  # kriterijus nuorodoms atrinkti (jei netyčia pasitaikytų papildomų)

        # Automatiškai keičiamas kintamasis per f-ją self.identifikuoti_priklausomas_rinkmenas()
        self.lentelės = []  # konteineris lentelėms/rinkmenoms kuriamoms su klase „Lentelė“

    def info(self, su_lentelėmis=False):
        """
        Pateikiama informacija apie rinkinį
        :param su_lentelėmis:
            True - papildomai pateikti išsamią informaciją apie susietas lenteles,
            False - nepateikti (numatyta)
        """
        print('\nRinkinys „%s“:\n'
              ' tipas: %s\n'
              ' aprašymas: %s %s'
              % (self.rinkinys, self.rinkinio_tipas, self.pilnas_pavadinimas, self.rinkinio_url)
              )
        for raktas in ['šaltinis', 'licencija']:  # nebūtinos self savybės
            if hasattr(self, raktas):  # jei savybę turi
                print(f' {raktas}: {self.__getattribute__(raktas)}')  # parašyti jos reikšmę
        if self.metai:
            # jei self.metai_nuo == self.metai_iki, tai parašys tik vieną skaičių; jei skiriasi, parašys per brūkšnelį
            print(' metai:', self.metai_tekstu())
        if su_lentelėmis:  # jei naudotojas prašo pateikti lenteles
            for lentelė in self.lentelės:  # apie kiekvieną lentelę atskirai
                lentelė.info(glaustas=True)  # pateikti trumpą lentelės informaciją vienoje eilutėje
            print()  # tuščia eilutė
        else:
            print(' turi lentelių: %d' % len(self.lentelės))  # tik parašyti lentelių skaičių be papildomos informacijos

    @abstractmethod
    def sutvarkyti_duomenis_savitai(self, df):  # abstraktus metodas
        """
        Surinktus duomenis paruošti analizei, t.y. išvalyti ir sutvarkyti priklausomai nuo tipo.
        :param df: naudotojas gali paduoti savo duomenis tvarkymui, bet numatytuoju atveju jie automatiškai paimami
        """
        pass  # vaikinės klasės privalės apsibrėžti metodus, o čia nieko nedaryti

    def sutvarkyti_duomenis(self, df=None, perdaryti=True, interaktyvus=True, ar_išsamiai=False):
        """
        Surinktus duomenis paruošti analizei, t.y. išvalyti ir sutvarkyti.
        Papildomai iškviečiama .sutvarkyti_duomenis_savitai()
        :param df: naudotojas gali paduoti savo duomenis tvarkymui, bet numatytuoju atveju jie automatiškai paimami
        :param perdaryti: [True|False], numatyta False - jei yra išsaugota rinkinio rinkmena, bandyti ją nuskaityti
        :param interaktyvus: jei perdaryti=False, ir self.rinkinio_rinkmena iš tiesų yra diske,
        tada ar klausti dėl jos pakartotinio naudojimo (numatytuoju atveju - True)
        :param ar_išsamiai: [True|False] ar rodyti/slėpti paaiškinimus
        """
        print()

        # Duomenys
        if df is None:
            # Pirmiausia įsikelti visus rinkiniui priklausančius duomenis į pd.DataFrame
            df = self.nuskaityti(perdaryti=perdaryti, interaktyvus=interaktyvus, ar_išsamiai=False)
            if df is None:
                return None  # žemesnio lygio klaida, greičiausiai jau aprašyta
            naudojami_naudotojo_duomenys = False  # tai vėliau pravers f-jos pabaigoje
        elif isinstance(df, pd.DataFrame):  # ar naudotojas tikrai pateikia pd.DataFrame tvarkymui?
            naudojami_naudotojo_duomenys = True  # tai vėliau pravers f-jos pabaigoje
        else:
            raise Exception('Nautotojo pateikti duomenys nėra pandas.DataFrame')

        # Patikrinti, ar turime visus norimus stulpelius
        trūkstami_stulpeliai_netvark = list(set(self.privalomi_stulpeliai_nesutvarkytiems) - set(list(df.columns)))
        if trūkstami_stulpeliai_netvark:
            if not list(set(self.privalomi_stulpeliai_sutvarkytiems) - set(list(df.columns))):  # o gal jau sutvarkyti?
                if ar_išsamiai:
                    print(f'Matyt „{self.rinkinio_tipas}“ duomenys jau sutvarkyti, '
                          f'nes yra būtini stuleliai ir nėra nesutvarkytiems duomenims būdingų stulpelių',
                          # trūkstami_stulpeliai_netvark
                          )
                return df
            else:
                if perdaryti or naudojami_naudotojo_duomenys:  # jei naudotojo arba naujai perdaryti duomenys
                    raise Exception(f'Duomenų tvarkymui trūksta šių stulpelių:', trūkstami_stulpeliai_netvark)
                else:
                    print(f'Duomenų tvarkymui trūksta šių stulpelių:', trūkstami_stulpeliai_netvark)
                    print('Nors neprašėte perdaryti duomenų, tačiau tai yra būtina! Bandoma iš naujo...')
                    df = self.sutvarkyti_duomenis(  # rekursija
                        df=None, perdaryti=True, interaktyvus=interaktyvus, ar_išsamiai=ar_išsamiai
                    )
                    return df

        """
        Pagrindiniai tvarkymo darbai, specifiškai besiskiriantys tarp rinkinių tipų
        """
        if naudojami_naudotojo_duomenys:
            print('Tvarkomi naudotojo pateikti duomenys taip, tarsi jie būtų tipo „%s“' % self.rinkinio_tipas)
        else:
            print('Tvarkomi rinkinio „%s“ duomenys...' % self.rinkinys)
        df = self.sutvarkyti_duomenis_savitai(df)
        print('Duomenų rinkinys „%s“ sutvarkytas ir paruoštas tolesnei analizei.' % self.rinkinys)

        # išsaugoti išvalytus duomenis
        if not naudojami_naudotojo_duomenys:  # rašyti į CSV tik tuo atveju, jei jie nėra naudotojo laikinas df
            self.saugoti_kaip_sutvarkytus(df, interaktyvus=interaktyvus)

        return df  # grąžinti duomenis analizei

    def nuskaityti(self, perdaryti=False, interaktyvus=True, ar_išsamiai=True):
        """
        Nuskaityti duomenis: arba įkelti iš rinkinio rinkmenos sutvarkytus, arba iš naujo surinkti juos (bet netvarkyti)
        :param perdaryti: [True|False], numatyta False - jei yra išsaugota rinkinio rinkmena, bandyti ją nuskaityti
        :param interaktyvus: [True|False], numatyta True - jei perdaryti=False ir self.rinkinio_rinkmena iš tiesų yra
        diske, tada klausti dėl jos pakartotinio naudojimo
        :param ar_išsamiai: [True|False] - ar rodyti (True - numatyta), ar slėpti (False) papildomus paaiškinimus
        """

        # Patikrinti, galbūt duomenys jau surinkti į vieną jungtinę rinkmeną?
        if (not perdaryti) and os.path.exists(self.rinkinio_rinkmena):  # ar yra diske? jei leidžia neperdaryti - imti
            print(f'Radome jau surinktus ir išsaugotus duomenis rinkmenoje „{self.rinkinio_rinkmena}“')
            while True:  # ciklas
                if interaktyvus:
                    naudotojo_įved = input('Ar rinkti naujai? Įveskite TAIP arba [NE]: \n> ')
                else:
                    naudotojo_įved = ''  # simuliuoti naudotojo įvedimą
                if naudotojo_įved.lower() in ['n', 'ne', '']:  # nieko neįvedus interpretuoti kaip NE
                    print('Toliau bus naudojami ankstesni duomenys')  # greičiausiai sutvarkyti duomenys, bet nebūtinai
                    df = pd.read_csv(self.rinkinio_rinkmena)  # išeiti iš funkcijos ir grąžinti senos rinkmenos turinį
                    trūkstami_stulpeliai_T = list(set(self.privalomi_stulpeliai_sutvarkytiems) - set(list(df.columns)))
                    if trūkstami_stulpeliai_T:
                        self.ar_duomenys_sutvarkyti = False
                        if ar_išsamiai:
                            print(f'Kaip sutvarkytiems duomenims trūktų stulpelių: {", ".join(trūkstami_stulpeliai_T)}')
                            if list(set(self.privalomi_stulpeliai_nesutvarkytiems) - set(list(df.columns))):
                                print('Taip pat nėra ir nesutvarkytiems duomenims būdingų stulpelių. Patikrinkite.')
                    if 'Data_laikas' in df.columns:  # konvertuoti į datą vėl, nes įkėlus iš CSV nusimuša
                        df['Data_laikas'] = pd.to_datetime(df['Data_laikas'], yearfirst=True, format='mixed', utc=True)
                    if 'Data' in df.columns:  # konvertuoti į datą vėl, nes įkėlus iš CSV nusimuša
                        df['Data'] = pd.to_datetime(df['Data'], yearfirst=True)

                    return df
                elif naudotojo_įved.lower() in ['t', 'taip']:
                    df = self.surinkti_duomenis(ar_išsamiai=ar_išsamiai)  # įkelti surinktus duomenis
                    break  # nutraukti ciklą, bet tęsti f-ją toliau
        else:
            df = self.surinkti_duomenis(ar_išsamiai=ar_išsamiai)  # surinkti juos iš pradinių duomenų naujai

        if ar_išsamiai and (df is not None):  # self.surinkti_duomenis() grąžina None klaidos atveju
            print(f'Nuskaitytieji ir grąžinami „{self.rinkinio_tipas}“ tipo duomenys greičiausiai',
                  'yra' if self.ar_duomenys_sutvarkyti else 'nėra', 'sutvarkyti')
        return df

    def surinkti_duomenis(self, ar_išsamiai=True):
        """
        Sujungia pirmines neapdorotas rinkmenas į vieną pandas.DataFrame, bet jų netvarko ir į diską neįrašo.
        Tos neapdorotos rinkmenos/lentelės gali būti nuotolinės arba vietinės; nuotolines parsiunčia naudojimui
        :param ar_išsamiai: [True|False] ar rodyti/slėpti paaiškinimus
        """

        # Patikrinti, ar turime susietas pradines neapdorotas duomenų nuotolines arba vietines rinkmenas
        if not self.lentelės:  # ar turime susietų rinkmenų sąrašą?
            print('Rinkinys', self.rinkinys, 'dar neturi duomenų.',
                  ('Matyt nepavyko jų automatiškai rasti tikrinant ' + self.rinkinio_url) if self.rinkinio_url else '')
            if self.katalogas_paskiroms_rinkmenoms:
                print('Padėkite pavienes %s rinkmenas kataloge %s ir iškvieskite '
                      '.identifikuoti_priklausomas_rinkmenas() ir .surinkti_duomenis() vėl.'
                      % (', '.join(f.upper() for f in self.formatai), self.katalogas_paskiroms_rinkmenoms))
            return None

        print('Surenkami rinkinio „%s“ duomenys...' % self.rinkinys)
        pavykusių_skaičius = 0  # skaitiklis
        df = pd.DataFrame()  # rezertuoti kintamąjį, kad PyCharm nerodytų įspėjimo:
        #  Local variable 'df' might be referenced before assignment
        for rinkmena in self.lentelės[::-1]:  # imti atvirkščia tvarka, kad pašalinus eigoje nebūtų praleista nei viena
            if (self.ar_saugoti_paskiras_rinkmenas and  # jei naudotojas nori išsisaugoti pradines rinkmenas ir:
                    (self.rinkinio_tipas == 'orai' or  # jei tipas yra orai, nes net vietinės gali būti virtualios
                     not tikrinti_ar_vietinė(rinkmena.lentelės_vieta))):  # arba rinkmena yra nuotolinė
                rinkmena.pakeisti_vietine(
                    os.path.join(self.katalogas_paskiroms_rinkmenoms, rinkmena.vardas),  # iškart nurodyti pilną kelią
                    ar_išsamiai=ar_išsamiai  # jei norėtume slėpti paaiškinimus
                )
            df1 = rinkmena.nuskaityti()  # nuskaityti vietinę arba nuotolinę rinkmeną
            ar_tinkama_lentelė1 = False  # Numatytoji reikšmė, bet pavykus ji pakeisima
            if df1 is not None:
                # Stulpelių pavadinimų tikrinimas, jei tokie nurodyti tikrinimui ir pervadinimui
                if hasattr(self, 'stulpelių_sinonimai'):  # galimi stulpelių sinonimai
                    stulp_nj_N = len(list(df1.columns))  # naujų stulpelių skaičius
                    if (  # ar tokie nauji stulpeliai iš anksto žinomi ir leistini
                            (stulp_nj_N in self.stulpelių_sinonimai) and  # tas skaičius yra tarp raktų
                            (list(df1.columns) in self.stulpelių_sinonimai[stulp_nj_N])  # nauji st. leistini
                    ):
                        df1.columns = self.stulpelių_sinonimai[stulp_nj_N][0]  # pervadinti stulpelius
                trūksta_tvar = list(set(self.privalomi_stulpeliai_sutvarkytiems) - set(list(df1.columns)))  # sutvarkyti
                trūksta_netv = list(set(self.privalomi_stulpeliai_nesutvarkytiems) - set(list(df1.columns)))  # netvark.
                if len(trūksta_tvar) and len(trūksta_netv):  # jei stulpelių pavadinimų trūksta
                    if ar_išsamiai:
                        print('Tikėtasi rasti stulpelius:', self.privalomi_stulpeliai_nesutvarkytiems,
                              'arba', self.privalomi_stulpeliai_sutvarkytiems)
                else:
                    ar_tinkama_lentelė1 = True

            ar_tinkama_lentelė2 = False  # Numatytoji reikšmė, bet pavykus ji pakeisima
            if ar_tinkama_lentelė1:
                df1['Laikotarpis'] = rinkmena.laikotarpis  # stulpelis, padėsiantis po sujungimo atskirti lenteles
                if pavykusių_skaičius:  # jei jau pavyko nuskaityti bent vieną, tai jau bus df kintamasis
                    if list(df.columns) == list(df1.columns):  # stulpelių pavadinimai sutampa
                        ar_tinkama_lentelė2 = True
                        df = pd.concat([df, df1], axis=0)  # prijungti eilutes
                    else:  # netinkami duomenys
                        print(' Nesutampa stulpeliai tarp lentelių:')
                        print('- Anksčiau įkeltų duomenų:\n     ', list(df.columns))
                        print(f'- {rinkmena.vardas} turi:\n     ', list(df1.columns))
                else:  # tai pirmoji sąrašo lentelė, kurią pavyko nuskaityti
                    ar_tinkama_lentelė2 = True
                    df = df1

            if ar_tinkama_lentelė2:
                pavykusių_skaičius += 1
            else:
                if ar_išsamiai:
                    print(' Nepavykus paimti duomenų iš <%s>, ši lentelė pašalinama iš rinkinio „%s“'
                          % (rinkmena.lentelės_vieta, self.rinkinys))
                self.lentelės.remove(rinkmena)
        if pavykusių_skaičius:
            print(f'Pavyko nuskaityti ir apjungti „{self.rinkinio_tipas}“ tipo lenteles:', pavykusių_skaičius)
            return df
        else:
            print(f'Nepavyko rasti nei vienos tinkamos „{self.rinkinio_tipas}“ tipo lenteles.')
            return None

    def saugoti_kaip_sutvarkytus(self, df, interaktyvus=True):
        if os.path.isfile(self.rinkinio_rinkmena):
            if interaktyvus:
                while True:
                    pasirinkimas = input(
                        f'Rinkmena {self.rinkinio_rinkmena} jau yra. Perrašyti? Įveskite [TAIP] arba NE:\n> '
                    )
                    if pasirinkimas.lower() in ['n', 'ne']:
                        return  # išeiti iš metodo, nieko nerašyti
                    elif pasirinkimas.lower() in ['t', 'taip', '']:  # nieko neįvedus (t.y. '') interpretuoti kaip TAIP
                        break  # išeiti iš ciklo, kad galėtų rašyti į csv
            else:
                print(f'Rinkmena {self.rinkinio_rinkmena} jau yra. Perrašysime ją')

        df.to_csv(self.rinkinio_rinkmena, index=False)
        self.ar_duomenys_sutvarkyti = True  # pažymėti duomenų rinkinį kaip sutvarkytą
        print('Sujungtus ir sutvarkytus duomenis rasite:', self.rinkinio_rinkmena)

    def identifikuoti_priklausomas_rinkmenas(self, laikotarpis=None):
        """
        Surenka nutolusių arba vietinių rinkmenų sąrašą (kas prieinama)
        Tinka Elektros ir Gyventojų duomenims, tačiau Orai turės modifikuotą versiją
        """

        # užmiršti ankstesnę informaciją apie paskiras rinkmenas, jei pakartotinai kviečiama f-ja
        self.lentelės = []

        # papildomi kintamieji
        licencija = (self.licencija if hasattr(self, 'licencija') else None)
        šaltinis = (self.šaltinis if hasattr(self, 'šaltinis') else None)

        # Ištraukia nuorodas iš duomenų portalo puslapio neparsiunčiant pačių duomenų
        # Jei kartais pirma norėtume matyti visas prieinamas rinkmenas ir jų laikus ir tik po to apsispręsti, ką siųstis
        nutolusios_rinkmenos = išrinkti_nuorodas_iš_puslapio(  # iš internetinio aprašo surinkti nuorodas į duomenis
            self.rinkinio_url, lentelės_požymiai=self.html_lentelės_požymiai,
            nuorodos_tekstas=self.html_nuorodos_tekstas
        )
        if nutolusios_rinkmenos:  # ar pavyko rasti nuorodų į nuotolines rinkmenas?
            print('Rinkiniui %s pavyko rasti nuotolines rinkmenas: %d' % (self.rinkinys, len(nutolusios_rinkmenos)))
            # Įsimintas rastas nuorodas kaip rinkiniui priklausančias lenteles, nes
            # jei jau pavyko gauti sąrašą internetu, greičiausiai pavyks pasiekti ir pačias rinkmenas
            self.lentelės = [
                Lentelė(rinkmena, tipas=self.rinkinio_tipas, licencija=licencija, šaltinis=šaltinis)
                for rinkmena in nutolusios_rinkmenos
            ]
        else:  # jei nepavyko internetu pasiekti duomenų
            # Gal turime vietines rinkmenas?
            if os.path.exists(self.katalogas_paskiroms_rinkmenoms):  # jei katalogas yra
                vietines_rinkmenos = os.listdir(self.katalogas_paskiroms_rinkmenoms)  # gauti rikmenų kataloge sąrašą
                # atrinkti tik tas, kurių galūnė yra atitinka formatą
                vietines_rinkmenos = [f for f in vietines_rinkmenos if (f.split('.')[-1] in self.formatai)]
                print('Rinkiniui %s pavyko rasti vietines rinkmenas: %d' % (self.rinkinys, len(vietines_rinkmenos)))
                self.lentelės = [Lentelė(
                    os.path.join(self.katalogas_paskiroms_rinkmenoms, rinkmena),
                    tipas=self.rinkinio_tipas, licencija=licencija, šaltinis=šaltinis
                ) for rinkmena in vietines_rinkmenos
                ]
        # Jokių duomenų?
        if not self.lentelės:  # jei jokiu išbandytu būdu nepavyko surinkti pirminių rinkmenų
            raise Exception(
                'Nepavyko nei parsisiųsti iš <%s>, nei rasti vietinių duomenų kataloge „%s“, '
                % (self.rinkinio_url, self.katalogas_paskiroms_rinkmenoms)
            )

        # Patikrinti laikotarpius
        self.atrinkti_pagal_laikotarpius(laikotarpis)

    def patikrink_laikotarpio_įvedimą(self, laikotarpis):
        """
        Patikrina naudotojo įvestą laikotarpį
        :param laikotarpis: metai kaip vienas skaičius arba sąrašas
        :return: metų sąrašas arba self.metai reikšmė (gali būti None)
        """
        if laikotarpis is None:  # nenurodytas
            laikotarpis = self.metai  # imti numatytąsias rinkinio reikšmes, sąrašas
        elif type(laikotarpis) in [int, float]:
            laikotarpis = [laikotarpis]  # paversti sąrašu
        elif isinstance(laikotarpis, list) and len(laikotarpis) > 0:  # pateiktas sąrašas?
            if all(isinstance(m, int) for m in laikotarpis):
                if len(laikotarpis) == 2:
                    laikotarpis = list(range(laikotarpis[0], laikotarpis[1] + 1))
                else:
                    pass  # primti metų sąrašą kaip laikotarpį tokį, koks yra
            else:
                print(' Įspėjimas: pasirinktas laikotarpis turėjo būti metai arba jų sąrašas, tad ignoruojama')
                laikotarpis = self.metai
        else:
            print(' Įspėjimas: pasirinktas laikotarpis turėjo būti metai (skaičius) arba jų sąrašas, tad ignoruojama')
            laikotarpis = self.metai
        return laikotarpis

    def atrinkti_pagal_laikotarpius(self, laikotarpis):
        """
        Galima papildomai išrinkti tik tas priklausančias lenteles, kurios atitinka pasirinktus metus
        :param laikotarpis: metai kaip vienas skaičius arba sąrašas
        """
        laikotarpis = self.patikrink_laikotarpio_įvedimą(laikotarpis)  # patikrinimas

        if laikotarpis:
            lentelių_skaičius_prieš = len(self.lentelės)
            self.lentelės = [lnt for lnt in self.lentelės
                             if (int(lnt.laikotarpis) in laikotarpis) or (lnt.laikotarpis in laikotarpis)
                             ]
            lentelių_skaičius_po = len(self.lentelės)
            if lentelių_skaičius_prieš != lentelių_skaičius_po:
                print(' Pasirinktą laikotarpį atitiko lentelės:', lentelių_skaičius_po)

        # atnaujinti self.metai savybę
        self.metai = sorted(set([int(lnt.laikotarpis) for lnt in self.lentelės]))

    def atnaujinti_rinkinio_rinkmenos_vardą(self, naujas_vardas=None):
        """
        Naujas vardas rinkinio rinkmenai
        :param naujas_vardas:
        """
        if naujas_vardas is None:
            self.rinkinio_rinkmena = os.path.join(
                self.katalogas_saugojimui,
                # katalogas ir rinkmena; prie pastarosios prirašyti laikotarpį, jei nurodytas
                self.rinkinys + ('_' + self.metai_tekstu() if self.metai else '') + '.csv'
            )
        else:
            self.rinkinio_rinkmena = str(naujas_vardas)
        print('Atnaujinta rinkinio „{}“ rinkmenos vieta: {}'.format(self.rinkinys, self.rinkinio_rinkmena))

    def metai_tekstu(self):
        # kovertuoja metų skaičių į tekstą
        if self.metai:
            if len(self.metai) == 1:
                metai_str = str(int(self.metai[0]))
            else:
                metai_str = '%d-%d' % (min(self.metai), max(self.metai))
        else:
            metai_str = ''
        return metai_str


class RinkinysElektrai(Rinkinys):
    """
    Elektros suvartojimo duomenys, kuriuos galima rasti Lietuvos atvirų duomenų portale pateikstus pamėnesiui CSV
    https://data.gov.lt/
    """

    def __init__(self, rinkinio_id='buitis', metai_nuo=None, metai_iki=None, ar_saugoti_paskiras_rinkmenas=True):
        """
        Inicijuoti elektros vartojimo duomenų struktūrą, surinkti rinkmenų sąrašą, bet pačių duomenų dar neparsisiųsti
        :param rinkinio_id: „buitis“ arba „verslas“
        """

        # Rinkinys: „buitis“ arba „verslas“. Patikrinti rinkinio vardą ir priskirti URL
        if rinkinio_id.lower() in ['b', 'buit', 'buitis', 'buitinių', 'buitiniai']:
            rinkinio_id = 'buitis'  # duomenys nuo 2021-01-01
            rinkinio_url = 'https://data.gov.lt/datasets/1778/'  # HTML puslapis turi lentelę su nuorodomis į CSV
            pilnas_pavadinimas = 'Automatizuotų buitinių vartotojų valandiniai duomenys agreguoti pagal regioną'
        elif rinkinio_id.lower() in ['v', 'vers', 'verslo', 'verslas']:
            rinkinio_id = 'verslas'  # duomenys nuo 2021-04-01
            rinkinio_url = 'https://data.gov.lt/datasets/1907/'  # HTML puslapis turi lentelę su nuorodomis į CSV
            pilnas_pavadinimas = 'Automatizuotų verslo vartotojų valandiniai duomenys agreguoti pagal regioną'
        else:
            klaidos_txt = f'Nežinomas rinkinio ID „{rinkinio_id}“. Palaikomi rinkinių ID: buitis, verslas'
            raise AttributeError(klaidos_txt)

        # Paveldėti iš bendras savybes iš tėvinės klasės Rinkinys
        super().__init__(
            rinkinio_tipas='elektra', rinkinio_url=rinkinio_url, pilnas_pavadinimas=pilnas_pavadinimas,
            metai_nuo=metai_nuo, metai_iki=metai_iki, ar_saugoti_paskiras_rinkmenas=ar_saugoti_paskiras_rinkmenas
        )
        self.rinkinio_id = rinkinio_id
        self.šaltinis = 'AB „Energijos skirstymo operatorius“ (ESO)'
        self.licencija = 'CC BY 4.0'  # pastrosios savybės bendrasis Rinkinys neturi
        # self.saugykla = 'https://data.gov.lt/'  # svetainė, kurioje talpinamos elektros duomenų CSV rinkmenos

        self.html_lentelės_požymiai = {'id': "resource-table"}
        self.html_nuorodos_tekstas = 'Atsisiųsti'
        self.rinkinys = self.rinkinio_tipas + '_' + rinkinio_id  # naudojamas katalogo vardui suformuoti
        self.rinkinio_rinkmena = os.path.join(
            self.katalogas_saugojimui,  # katalogas ir rinkmena; prie pastarosios prirašyti laikotarpį, jei nurodytas
            self.rinkinys + ('_' + self.metai_tekstu() if self.metai else '') + '.csv'
        )
        self.katalogas_paskiroms_rinkmenoms = os.path.join(self.katalogas_saugojimui, self.rinkinys)  # pradiniams
        self.formatai = ['csv']  # palaikomi rinkmenų formatai ieškant vietinių rinkmenų
        self.privalomi_stulpeliai_sutvarkytiems = [
            'Regionas', 'Suvartojimas (kWh/val)', 'Abonentai',
            'Metai', 'Mėnuo', 'Metai-mėnuo', 'Data', 'Sav. diena', 'Valanda'
        ]  # Nebūtini: 'Data_laikas', 'Laikotarpis', 'Diena', 'Vid. reg. ab. suvartojimas (kWh/val)',
        self.privalomi_stulpeliai_nesutvarkytiems = ['GR_NAME', 'PL_T', 'P+', 'OBJ_COUNT']  # ir gal 'Laikotarpis'
        self.identifikuoti_priklausomas_rinkmenas()

    def sutvarkyti_duomenis_savitai(self, df):
        """
        Surinktus elektros duomenis paruošti analizei, t.y. išvalyti ir sutvarkyti
        :param df: naudotojas gali paduoti savo duomenis tvarkymui, bet paprastai turėtų paduoti .sutvarkyti_duomenis()
        """

        """
        Darbas su esamais stulpeliais (iki papildomų/išvestinių duomenų pridėjimo)
        """

        # Stulpelių atranka
        df = df[self.privalomi_stulpeliai_nesutvarkytiems]

        # Persivadinti stulpelius
        df = df.rename(columns={
            'GR_NAME': 'Regionas',  # regionas
            'PL_T': 'Data_laikas',  # Data ir laikas, pvz., '2023-11-30 17:00:00'
            'P+': 'Suvartojimas (kWh/val)',  # per valandą iš skirstomojo tinklo suvartotas elektros kiekis (kWh)
            'OBJ_COUNT': 'Abonentai'  # suminis vartotojų skaičius regione
        })

        # Valymas
        df = df.dropna()  # išmesti eilutes, kur bent viena reikšmė yra NA

        # Reikšmių pervadinimas
        # ESO atskiria Vilniaus miestą ir Vilniaus rajoną, bet orai yra tiesiog Vilniaus:
        # jei norime išlaikyt Vilniaus rajoną ir Vilniaus miestą atskirai:
        # palikti tik pirmuosius žodžius: nereikia jokių prierašų kaip „ miesto“, „ rajono“
        # df['Regionas'] = df['Regionas'].replace(' Vartotojai', '', regex=True)  # atmesti žodį „ Vartotojai“
        # jei nereikia Vilniaus rajono ir miesto atskirai
        df['Regionas'] = df['Regionas'].apply(lambda x: x.split(' ')[0])  # imti tik pirmąjį žodį

        # Laiko ir Regiono stulpelius padaryti pirmuosius
        stulpeliai_pirmieji = ['Data_laikas', 'Regionas']  # jie bus kairiausiai
        stulpeliai_paskutiniai = list(df.columns)  # iš pradžių tai visi stulpeliai, bet iš jų pašalinsim kai kuriuos
        for laikinai_atmetamas in stulpeliai_pirmieji:
            stulpeliai_paskutiniai.remove(laikinai_atmetamas)  # išimti po vieną stulpelio pavadinimą
        df = df[stulpeliai_pirmieji + stulpeliai_paskutiniai]  # perrikiuoti pagal naują eiliškumą

        """
        Klaida https://data.gov.lt/media/filer_public/74/99/74996afc-6ed2-4f96-8ced-cff077eedcae/2021_03_buitis.csv
        reikia pataisyti 2021_03_buitis.csv nesistemingai naudojamą dešimtainį skirtuką: 
        didelėje dokumento dalyje naudojamas kablelis (nuo Akmenės iki Varėnos), bet pabaigoje naudojamas taškas
        (Vilniaus miesto, Vilniaus rajono, Zarasų, Šakių, Šalčininkų, Šiaulių, Šilalės, Šilutės, Širvintų, Švenčionių)
        """
        blogi = df[df['Suvartojimas (kWh/val)'].apply(lambda x: isinstance(x, str))]
        if len(blogi):
            print(' Netvarka „Suvartojimas (kWh/val)“ stulpelyje: tekstas ten, kur tikėtasi skaičių.')
            if 'Laikotarpis' in df.columns:
                blogas_laikotarpis = blogi.groupby('Laikotarpis')['Laikotarpis'].unique()
                print('  Blogi laikotarpiai:',
                      [f'{int(x)}-{round((x - int(x)) * 12) + 1:02d}' for x in blogas_laikotarpis.index])  # metai-mėnuo
            print('  Bandoma taisyti automatiškai...')
            df['Suvartojimas (kWh/val)'] = df['Suvartojimas (kWh/val)'].apply(  # sėkmingai pataiso 2021_03_buitis.csv
                lambda x: float(x.replace(',', '.')) if isinstance(x, str) else float(x)
            )
            # žemesnės dalies nereikia su 2021-2023 metų duomenimis - tik dėl visa ko patestavimui
            blogi = df[df['Suvartojimas (kWh/val)'].apply(lambda x: isinstance(x, str))]
            if len(blogi):  # atsargumo dėlei patikrinti
                print(' Netvarka „Suvartojimas (kWh/val)“ stulpelyje vis tiek liko: tekstas ten, kur tikėtasi skaičių.')
                if 'Laikotarpis' in df.columns:
                    blogas_laikotarpis = blogi.groupby('Laikotarpis')['Laikotarpis'].unique()
                    print('  Lilko blogi laikotarpiai:',
                          [f'{int(x)}-{round((x - int(x)) * 12) + 1:02d}' for x in blogas_laikotarpis.index])
                print('Netvarkingos eilutės išmetamos iš analizės')
                # pavyzdys, kaip būtų buvę galima valyti, jei nebūtų pasisekę sutvavryti 2021_03_buitis.csv
                df = df[df['Suvartojimas (kWh/val)'].apply(lambda x: not isinstance(x, str))]
            else:
                print(' Klaida duomenyse ištaisyta sėkmingai.')
        # Po tikrinimų laikotarpio kintamasis nebereikalingas:
        if 'Laikotarpis' in df.columns:
            df = df.drop(['Laikotarpis'], axis=1)

        """ Vasaros / žiemos laikas, laiko juostos """
        # Atmesti pasikartojusį laiką 2021-03-28 04:00:00 2021_03_buitis.csv duomenyse:
        # Alytaus Vartotojai;2021-03-28 02:00:00.000;94,7937;744
        # Alytaus Vartotojai;2021-03-28 04:00:00.000;92,4336;742  <- 4 val., žiemos laikas?
        # Alytaus Vartotojai;2021-03-28 04:00:00.000;84,95895;744 <- 4 val., vasaros laikas?
        # Alytaus Vartotojai;2021-03-28 05:00:00.000;89,5975;744
        df.drop_duplicates(subset=['Data_laikas', 'Regionas'], keep=False)

        # Tačiau daugiau duomenyse tokių atvejų nėra.
        # Vizualiai tikrinta, kaip vasarį, balandį, rugsėjį ir lapkritį išsidėsto elektros vartojimas:
        # Labai aiški vienos valandos skirtis tarp žiemiškesnių ir vasariškesnių mėnesiui.
        # Vadinasi, greičiausiai duomenyse yra UTC laiko juosta, o ne vietinė laiko juosta.

        # Kovertuoti į datos / laiko tipą; laiko juosta yra UTC
        df['Data_laikas'] = pd.to_datetime(df['Data_laikas'], format='mixed', yearfirst=True, utc=True)

        # Konvertuoti į vietinę laiko juostą:
        # jei tz_convert čia neveiktų, reiktų imti tz_localize su 'ambiguous' parametru dėl vasaros/žiemos laiko
        df['Data_laikas'] = df['Data_laikas'].dt.tz_convert('Europe/Vilnius')  # ambiguous='NaT'

        # Dar kartą naudoti dropna, tik dabar kad pašalintų dviprasmiškus/NaT laikus
        df = df.dropna()  # išmesti eilutes, kur bent viena reikšmė yra NA

        """
        Išvestiniai kintamieji/stulpeliai:
        """
        # Vieno abonento vidutinis suvartojimas regione per valandą
        df['Vid. reg. ab. suvartojimas (kWh/val)'] = df['Suvartojimas (kWh/val)'] / df['Abonentai']

        # Standartizuotos reikšmės. nauji kintamieji neturės vienetų, kurie buvo tarp skliaustų
        for kintamasis in ['Suvartojimas (kWh/val)', 'Vid. reg. ab. suvartojimas (kWh/val)']:
            naujo_kintamojo_pavad = re.sub(r' \(.+$', ' (st.)', kintamasis)
            df[naujo_kintamojo_pavad] = StandardScaler().fit_transform(df[[kintamasis]])

        # Datos ir laikas. Pradiniuose duomenyse formatai skiriasi: '%Y-%m-%d %H:%M:%S' "%Y-%m-%d %H:%M:%S.%f"
        df['Data_laikas'] = pd.to_datetime(df['Data_laikas'], format='mixed', yearfirst=True)
        df['Data'] = df['Data_laikas'].dt.to_period('D')  # Data, pvz., 2023-12-31
        df['Metai-mėnuo'] = df['Data_laikas'].dt.to_period('M')  # metai-mėnuo pvz., 2023-12 yra 2023 m. gruodis
        df['Metai'] = df['Data_laikas'].dt.year
        df['Mėnuo'] = df['Data_laikas'].dt.month
        # df['Diena'] = df['Data_laikas'].dt.day
        df['Sav. diena'] = df['Data_laikas'].dt.weekday + 1  # savaitės diena: standartiškai 0=pirmadienis, padidinti
        # atrinkti, kurios dienos buvo darbo, kurios šventinės ar savaitgaliai
        df['Darbadienis'] = ar_darbo_diena(df['Data_laikas'])
        df['Valanda'] = df['Data_laikas'].dt.hour

        # Po laiko juostų konvertavimo, kai kurie duomenys gali persislinkti į kitus metus
        if self.metai:
            df = df[df['Metai'].apply(lambda x: x in self.metai)]

        # Perrikiuoti
        df = df.sort_values(by=['Data_laikas', 'Regionas'], ignore_index=True)

        return df  # grąžinti duomenis


class RinkinysGyventojams(Rinkinys):
    """
    Registrų centro svetainėje pateiktos statistinės suvestinės lentelės apie
    gyventojų skaičius pagal savivaldybes su nuorodomis į Excel rinkmenas:
    https://www.registrucentras.lt/p/853
    """

    def __init__(self, metai_nuo=None, metai_iki=None, ar_saugoti_paskiras_rinkmenas=True):
        """
        Inicijuoti demografinių duomenų struktūrą, surinkti rinkmenų sąrašą, bet pačių duomenų dar neparsisiųsti
        """

        # Paveldėti iš bendras savybes iš tėvinės klasės Rinkinys
        super().__init__(
            rinkinio_tipas='gyventojai',
            rinkinio_url='https://www.registrucentras.lt/p/853',  # HTML puslapis turi lentelę su nuorodomis į Excel
            pilnas_pavadinimas='Gyventojų skaičius pagal savivaldybes',
            metai_nuo=metai_nuo, metai_iki=metai_iki, ar_saugoti_paskiras_rinkmenas=ar_saugoti_paskiras_rinkmenas
        )
        self.šaltinis = 'Registrų centras'
        # self.saugykla = 'https://www.registrucentras.lt/'  # svetainė, kurioje talpinamos Excel rinkmenos

        self.html_lentelės_požymiai = {'style': "width: 100%;"}
        self.html_nuorodos_tekstas = 'XLS'  # nuo 2020 metų; PDF yra nuo 2015 m.
        # self.rinkinys = self.rinkinio_tipas # naudojamas katalogo vardui suformuoti
        # self.katalogas_paskiroms_rinkmenoms = os.path.join(self.katalogas_saugojimui, self.rinkinys)
        self.formatai = ['xlsx', 'xls']  # kai kurios rinkmenos yra XLS, o kai kurios XLSX
        self.privalomi_stulpeliai_sutvarkytiems = ['Regionas', 'Gyventojai']
        self.privalomi_stulpeliai_nesutvarkytiems = ['Savivaldybės pavadinimas', 'Bendras gyventojų skaičius',
                                                     'Gyventojai 0–6 m.', 'Gyventojai 7–17 m.', 'Gyventojai 60 m. +']
        self.stulpelių_sinonimai = {  # Leidžiami sinonimai pagal stulpelių skaičių; 'Laikotarpis' yra automatinis
            6: [  # jei yra 6 stulpeliai, tai jų sinonimai:
                ['Eil. nr.', 'Savivaldybės pavadinimas', 'Bendras gyventojų skaičius', 'Gyventojai 0–6 m.',
                 'Gyventojai 7–17 m.', 'Gyventojai 60 m. +'],  # mūsų pageidaujamas
                ['Eil. nr.', 'Savivaldybės pavadinimas', 'Bendras gyventojų skaičius', 'Amžiaus grupės nuo 0 iki 6 m.',
                 'Amžiaus grupės nuo 7 m. iki 17 m.', 'Amžiaus grupės 60 m. +'],  # 2023 m.
                ['Eil. Nr.', 'Savivaldybės pavadinimas', 'Bendras gyventojų skaičius', 'Amžiaus grupės 0 - 6 m.',
                 'Amžiaus grupės 7 m. - 17 m.', 'Amžiaus grupės 60 m. +'],  # 2022 m.
                ['Eil. Nr.', 'Savivaldybės pavadinimas', 'Bendras gyventojų skaičius', 'Amžiaus grupės 0 - 6',
                 'Amžiaus grupės 7 - 17', 'Amžiaus grupės Pensinio amžiaus'],  # 2021 m.
                ['Eil. nr.', 'Savivaldybės pavadinimas', 'Bendras gyventojų skaičius', 'Amžiaus grupės 0–6',
                 'Amžiaus grupės 7–17', 'Amžiaus grupės Pensinio amžiaus']  # 2020 m.
            ]}
        self.identifikuoti_priklausomas_rinkmenas()

    def sutvarkyti_duomenis_savitai(self, df):
        """
        Surinktus orų duomenis paruošti analizei, t.y. išvalyti ir sutvarkyti
        :param df: naudotojas gali paduoti savo duomenis tvarkymui, bet paprastai turėtų paduoti .sutvarkyti_duomenis()
        """

        """ Darbas su esamais stulpeliais (iki papildomų/išvestinių duomenų pridėjimo) """

        # Valymas
        df.dropna(inplace=True)  # išmesti eilutes, kur bent viena reikšmė yra NA, pvz., eilutę „Iš viso:“

        # Persivadinti stulpelius
        df.rename(columns={
            'Bendras gyventojų skaičius': 'Gyventojai',
        }, inplace=True)

        """ Išvestiniai/papildomi kintamieji/stulpeliai: """

        # Gyventojų duomenyse yra kelios miestų savivaldybės (pvz.,
        # Vilniaus, Kauno, Klaipėdos, Šiaulių, Panevėžio, Alytaus, Palangos),
        # taip pat be miesto prierašų Birštono, Elektrėnų, Kalvarijos, Kazlų Rūdos, Neringos, Pagėgių, Rietavo, Visagino
        # be to, kai kur rašo "Vilniaus miesto sav." (pilniaus), o kai kur "Vilniaus m. sav." (trumpiau)
        # Tačiau ESO regionas atskiria Vilniaus miestą ir rajoną, o kitų miestų ir rajonų neskiria, nėra savivaldybių
        df['Regionas'] = df['Savivaldybės pavadinimas'].copy()
        # df['Regionas'] = df['Regionas'].replace('Vilniaus m.* sav.', 'Vilniaus miesto', regex=True)  # jei norim jo
        # df['Regionas'] = df['Regionas'].replace('Vilniaus r.* sav.', 'Vilniaus rajono', regex=True)  # jei norim jo
        df['Regionas'] = df['Regionas'].replace(' .*sav.', '', regex=True)

        df = df.groupby(['Regionas', 'Laikotarpis']).agg({
            'Gyventojai': 'sum', 'Gyventojai 0–6 m.': 'sum', 'Gyventojai 7–17 m.': 'sum', 'Gyventojai 60 m. +': 'sum'
        }).reset_index()

        df['Gyventojai 18-59 m.'] = (df['Gyventojai'] - df['Gyventojai 0–6 m.'] -
                                     df['Gyventojai 7–17 m.'] - df['Gyventojai 60 m. +'])

        sutvarkyti_kintamieji = ['Laikotarpis', 'Regionas', 'Gyventojai',
                                 'Gyventojai 0–6 m.', 'Gyventojai 7–17 m.', 'Gyventojai 18-59 m.', 'Gyventojai 60 m. +'
                                 ]

        # transformacija: standartizavimas
        for kintamasis in ['Gyventojai 0–6 m.', 'Gyventojai 7–17 m.', 'Gyventojai 18-59 m.', 'Gyventojai 60 m. +']:
            # Santykinė gyventojų dalis pagal amžiau grupes, %
            df[kintamasis + ' (%)'] = df[kintamasis] / df['Gyventojai'] * 100
            # Standartizuotos reikšmės
            df[kintamasis + ' (st.)'] = StandardScaler().fit_transform(df[[kintamasis + ' (%)']])
            sutvarkyti_kintamieji.extend([kintamasis + ' (%)', kintamasis + ' (st.)'])

        """ Baigiamieji darbai """
        # atsirinkti stulpelius:
        df = df[sutvarkyti_kintamieji]

        return df


class RinkinysOrams(Rinkinys):
    """
    Lietuvos hidrometeorologijos tarnyba prie Aplinkos ministerijos (LHMT) teikia meteorologinius duomenis
     ir platina juos <https://archyvas.meteo.lt/> pagal CC BY-SA 4.0 licenciją
    """

    def __init__(self, metai_nuo=None, metai_iki=None, ar_saugoti_paskiras_rinkmenas=True):
        super().__init__(
            rinkinio_tipas='orai',
            rinkinio_url='https://archyvas.meteo.lt/',  # HTML puslapis turi lentelę su nuorodomis į Excel
            pilnas_pavadinimas='LHMT meteorologinių stebėjimų archyvas',
            metai_nuo=metai_nuo, metai_iki=metai_iki, ar_saugoti_paskiras_rinkmenas=ar_saugoti_paskiras_rinkmenas
        )
        self.šaltinis = 'Lietuvos hidrometeorologijos tarnyba prie Aplinkos ministerijos (LHMT)'
        self.licencija = 'CC BY-SA 4.0'  # pastrosios savybės bendrasis Rinkinys neturi
        self.formatai = ['csv']  # HTML kode yra JavaScript, kintamojo struktūra JSON, bet konvertavus saugoma kaip CSV

        self.privalomi_stulpeliai_nesutvarkytiems = [
            'obs_time_utc', 'station_code', 'air_temperature', 'feels_like_temperature',
            'wind_speed', 'sea_level_pressure', 'relative_humidity', 'precipitation'
        ]
        # Visi galimi stulpeliai: (išsamesnius jų lietuviškus paaiškinimus rasite https://api.meteo.lt/ ir meteo_lt.py)
        # ['obs_time_utc', 'station_code', 'air_temperature', 'feels_like_temperature',
        # 'wind_speed', 'wind_gust', 'wind_direction', 'cloud_cover', 'sea_level_pressure',
        # 'relative_humidity', 'precipitation', 'condition_code', 'Laikotarpis']
        self.privalomi_stulpeliai_sutvarkytiems = [
            'Regionas', 'Temperarūra (C)', 'Vėjo greitis (m/s)', 'Slėgis (hPa)', 'Drėgnis (%)',
            'Kritulių kiekis (mm)', 'Metai', 'Mėnuo', 'Metai-mėnuo', 'Data', 'Sav. diena', 'Valanda'
        ]  # Nebūtini: 'Data_laikas', 'Juntamoji temperarūra (C)', 'Laikotarpis', 'Diena'
        self.meteo_stotys = meteo_lt.gauti_stotis()  # meteo_st_kodai = [stotis['code'] for stotis in self.meteo_stotys]
        self.identifikuoti_priklausomas_rinkmenas()

    def identifikuoti_priklausomas_rinkmenas(self, laikotarpis=None):
        # Perrašo tėvinės Rinkinys klasės identifikuoti_priklausomas_rinkmenas metodą
        """
        Surenka arba esamų vietinių rinkmenų sąreašą, arba bent teoriškai galimų rinkmenų sąrašą, kad kita f-ja žinotų,
        kokių raktažodžių ieškoti, nes tokių kaip nuotolinių orų rinkmenų nėra.
        """

        """
        Papildoma informacija:
        https://archyvas.meteo.lt/ neleidžia duomenų atsisiųsti per nuorodą, nors leidžia naršyklėje, pvz., atvėrus
        https://archyvas.meteo.lt/?station=vilniaus-ams&start_date=2023-01-01&end_date=2023-12-31&meteo-form=Rodyti
        ir pasirinkus CSV ir paspaudus „Atsisiųsti“: https://archyvas.meteo.lt/f94e79f6-6e1c-4536-91f2-503eedce32aa
        Siekiant suderinmumo su čia esančiu kodu, rankiniu būdu parsisiųstąsias rinkmenas reikia išsaugoti pagal schemą
         "{stoties_kodas}_{metai}.csv" (numatytuoju atveju naršyklė siūlo vieną ir tą patį pavadinimą nepaisant stoties 
         kodo ir nepaisant pasirinkto laikotarpio).
        """

        if self.meteo_stotys:  # jei pavyko pasiekti internetą ir gauti stočių sąrašą
            # Sukuriamas netikrų vietinių rinkmenų sąrašas, naudingas turėti prieš siunčiantis
            # Parsisiuntimą nesant rinkmenos užtikrins LentelėOrams klasės metodas .nuskaityti()
            self.lentelės = []  # pamiršti senas lenteles

            # laikotarpio apibrėžimas iš anksto
            if laikotarpis is None:
                laikotarpis = self.metai  # sąrašas
            elif type(laikotarpis) in [int, float]:
                laikotarpis = [laikotarpis]  # paversti sąrašu
            elif isinstance(laikotarpis, list) and len(laikotarpis) > 0:  # pateiktas sąrašas?
                if all(isinstance(m, int) for m in laikotarpis):
                    if len(laikotarpis) == 2:
                        laikotarpis = list(range(laikotarpis[0], laikotarpis[1] + 1))
                    else:
                        pass  # primti metų sąrašą kaip laikotarpį tokį, koks yra
                else:
                    print(' Įspėjimas: pasirinktas laikotarpis turėjo būti metai arba jų sąrašas, tad ignoruojama')
                    laikotarpis = self.metai
            else:
                print('Įspėjimas: pasirinktas laikotarpis turėjo būti metai (skaičius) arba jų sąrašas, tad ignoruojam')
                laikotarpis = None
            if laikotarpis:
                metai_nuo = max(min(laikotarpis), 2013)  # mažiausias iš nurodyto laikotarpio, bet ne mažesnis kaip 2013
                metai_iki = min(max(laikotarpis), datetime.date.today().year)  # didžiausias, bet tik iki šių metų
            else:
                metai_nuo = 2013  # meteo.lt duomenų archyve prieinami duomenys nuo 2013-10-10
                metai_iki = datetime.date.today().year  # iki šių metų

            for stotis in self.meteo_stotys:
                for metai in range(metai_nuo, metai_iki + 1):  # +1 dėl range() ypatybės neįtraukti imtinai antrojo sk.
                    # sukurti virtualią lentelę su kiekvienais orų stočių kodais ir metais
                    rinkmena = os.path.join(self.katalogas_paskiroms_rinkmenoms, f'%s_%d.csv' % (stotis['code'], metai))
                    lentelė = LentelėOrams(
                        rinkmena, meteo_stoties_kodas=stotis['code'], laikotarpis=metai,
                        šaltinis=self.šaltinis, licencija=self.licencija
                    )
                    self.lentelės.append(lentelė)
            print('Rinkiniui %s priskirtos virtualios rinkmenos: %d' % (self.rinkinys, len(self.lentelės)))

        # Jei nepavyko pasiekti interneto, sudaryti turimų vietinių lentelių sąrašą
        elif os.path.exists(self.katalogas_paskiroms_rinkmenoms):  # jei katalogas yra
            vietines_rinkmenos = os.listdir(self.katalogas_paskiroms_rinkmenoms)  # gauti rikmenų kataloge sąrašą
            # atrinkti tik tas, kurių galūnė yra atitinka formatą
            vietines_rinkmenos = [f for f in vietines_rinkmenos if (f.split('.')[-1] in self.formatai)]
            print('Rinkiniui %s pavyko rasti vietines rinkmenas: %d' % (self.rinkinys, len(vietines_rinkmenos)))
            self.lentelės = [
                LentelėOrams(
                    os.path.join(self.katalogas_paskiroms_rinkmenoms, rinkmena),
                    šaltinis=self.šaltinis, licencija=self.licencija
                )
                for rinkmena in vietines_rinkmenos
            ]

        # Patikrinti laikotarpius
        self.atrinkti_pagal_laikotarpius(laikotarpis)

    def sutvarkyti_duomenis_savitai(self, df):
        """
        Surinktus orų duomenis paruošti analizei, t.y. išvalyti ir sutvarkyti
        :param df: naudotojas gali paduoti savo duomenis tvarkymui, bet paprastai turėtų paduoti .sutvarkyti_duomenis()
        """

        """
        Darbas su esamais stulpeliais (iki papildomų/išvestinių duomenų pridėjimo)
        """

        # Stulpelių atranka
        df = df[self.privalomi_stulpeliai_nesutvarkytiems]

        # Valymas
        df = df.dropna()  # išmesti eilutes, kur bent viena reikšmė yra NA

        # Persivadinti stulpelius
        df = df.rename(columns={
            'obs_time_utc': 'Data_laikas',  # Data ir laikas, pvz., '2023-11-30 17:00:00'
            'air_temperature': 'Temperarūra (C)',  # Oro
            'feels_like_temperature': 'Juntamoji temperarūra (C)',
            'wind_speed': 'Vėjo greitis (m/s)',
            'sea_level_pressure': 'Slėgis (hPa)',
            'relative_humidity': 'Drėgnis (%)',
            'precipitation': 'Kritulių kiekis (mm)',  # mm per valandą
        })

        # Kovertuoti į datos / laiko tipą; laiko juosta yra UTC
        # Pradiniuose duomenyse formatai skiriasi: '%Y-%m-%d %H:%M:%S' "%Y-%m-%d %H:%M:%S.%f"
        df['Data_laikas'] = pd.to_datetime(df['Data_laikas'], format='mixed', yearfirst=True, utc=True)

        # Konvertuoti į vietinę laiko juostą:
        # jei tz_convert čia neveiktų, reiktų imti tz_localize su 'ambiguous' parametru dėl vasaros/žiemos laiko
        df['Data_laikas'] = df['Data_laikas'].dt.tz_convert('Europe/Vilnius')  # ambiguous='NaT'

        # Dar kartą naudoti dropna, tik dabar kad pašalintų dviprasmiškus/NaT laikus
        df = df.dropna()  # išmesti eilutes, kur bent viena reikšmė yra NA

        """
        Išvestiniai/papildomi kintamieji/stulpeliai:
        """
        # Regionai (praktiškai atitinka rajonus, savivaldybes)
        meteo_stotys_ir_rajonai = meteo_lt.stotys_ir_regionai(  # kaip stočių kodai susieja su regionais
            csv_rinkmena=os.path.join(self.katalogas_saugojimui, 'meteo_stotys_regionuose.csv')
        )
        df = df.merge(meteo_stotys_ir_rajonai[['station_code', 'Regionas']])  # prijungti regionus prie lentelės

        # stulpelis 'station_code' nebereikalingas, nes turime regionus
        df = df.drop(['station_code'], axis=1)

        # Perrikiuoti stulpelius
        stulpeliai_pirmieji = ['Data_laikas', 'Regionas']
        stulpeliai_paskutiniai = list(df.columns)  # iš pradžių tai visi stulpeliai, bet iš jų pašalinsim kai kuriuos
        for laikinai_atmetamas in stulpeliai_pirmieji:
            stulpeliai_paskutiniai.remove(laikinai_atmetamas)  # išimti po vieną stulpelio pavadinimą
        df = df[stulpeliai_pirmieji + stulpeliai_paskutiniai]  # perrrikiuoti pagal naują eiliškumą

        # transformacija: standartizavimas
        for kintamasis in [
            'Temperarūra (C)', 'Juntamoji temperarūra (C)', 'Vėjo greitis (m/s)',
            'Slėgis (hPa)', 'Drėgnis (%)', 'Kritulių kiekis (mm)'
        ]:
            # Standartizuotos reikšmės. nauji kintamieji neturės vienetų, kurie buvo tarp skliaustų
            naujo_kintamojo_pavad = re.sub(r' \(.+$', ' (st.)', kintamasis)
            df[naujo_kintamojo_pavad] = StandardScaler().fit_transform(df[[kintamasis]])

        # Datos ir laikas.
        df['Data'] = df['Data_laikas'].dt.to_period('D')  # Data, pvz., 2023-12-31
        df['Metai-mėnuo'] = df['Data_laikas'].dt.to_period('M')  # pvz., 2023-12 = 2023 m. gruodis
        df['Metai'] = df['Data_laikas'].dt.year
        df['Mėnuo'] = df['Data_laikas'].dt.month
        # df['Diena'] = df['Data_laikas'].dt.day
        df['Sav. diena'] = df['Data_laikas'].dt.weekday + 1  # savaitės diena: standartiškai 0=pirmadienis, tad padidint
        # atrinkti, kurios dienos buvo darbo, kurios šventinės ar savaitgaliai
        df['Darbadienis'] = ar_darbo_diena(df['Data_laikas'])
        df['Valanda'] = df['Data_laikas'].dt.hour

        # Po laiko juostų konvertavimo, kai kurie duomenys gali persislinkti į kitus metus
        if self.metai:
            df = df[df['Metai'].apply(lambda x: x in self.metai)]

        # Perrikiuoti eilutes
        df = df.sort_values(by=['Data_laikas', 'Regionas'], ignore_index=True)

        return df  # grąžinti duomenis


"""
Polimorfizmai
"""


def nuskaityti(rinkinys_arba_lentelė):
    if (hasattr(rinkinys_arba_lentelė, 'rinkinio_rinkmena') or  # ar rinkinys?
            hasattr(rinkinys_arba_lentelė, 'lentelės_vieta')):  # ar lentelė?
        return rinkinys_arba_lentelė.nuskaityti()
    else:
        print('Nežinau ką daryti, nes objektas nėra nei rinkinys, nei lentelė')
        return None


def sutvarkyti(rinkinys_arba_lentelė, *args, **kwargs):
    if hasattr(rinkinys_arba_lentelė, 'rinkinio_rinkmena'):  # ar rinkinys?
        return rinkinys_arba_lentelė.sutvarkyti_duomenis(*args, **kwargs)
    elif hasattr(rinkinys_arba_lentelė, 'lentelės_vieta'):  # ar lentelė?
        df = nuskaityti(rinkinys_arba_lentelė)
        if rinkinys_arba_lentelė.tipas == 'elektra':
            rinkinys = RinkinysElektrai()
        elif rinkinys_arba_lentelė.tipas == 'orai':
            rinkinys = RinkinysOrams()
        elif rinkinys_arba_lentelė.tipas == 'gyventojai':
            rinkinys = RinkinysGyventojams()
        else:
            print('Nepalaikokmas tipas:', rinkinys_arba_lentelė.tipas)
            return None
        return rinkinys.sutvarkyti_duomenis(df, *args, **kwargs)
    else:
        print('Nežinau ką daryti, nes objektas nėra nei rinkinys, nei lentelė')
        return None


"""
BENDRIEJI ĮRANKIAI:
"""


def tikrinti_ar_vietinė(kelias):
    """
    Tikrinti, ar kelias yra nuotolinis, ar vietinis pagal '://' buvimą; netikrina, ar jis realus
    :param kelias: vietinis kelias arba URL kaip tekstas
    :return:
    """
    # jei turi protokolą, sakyti kad nuotolinė, nors išimtiniais atvejais gali būti vietinė 'file://'
    return not ('://' in str(kelias))


def atrinkti_skaitmenis(tekstas, kiekis=None):
    """
    Grąžina tekste esančių skaitmenų junginį kaip teksto eilutę
    Pvz., gali padėti aptikti metus ir mėnesį pagal rinkmenos pavadinimą, kai tie pavadinimai labai skiriasi tarpusavy
    """

    # Įvedimo tikrinimas
    if type(tekstas) in [int, float]:
        tekstas = str(tekstas)
    elif type(tekstas) is not str:
        print('Pirmasis argumentas turi būtas tekstas arba skaičius')
        return ''
    if type(kiekis) is None:
        kiekis = len(tekstas)
    elif not (type(kiekis) is int):
        print('Antrasis argumentas kiekiui turi būti sveikasis skaičius arba None (visi skaimenys)')
        return ''

    # „Žodis“ tik iš skaimenų
    tik_skaimenys = ''
    for simbolis in tekstas:  # imti po vieną teksto simbolį
        if simbolis.isdigit() and len(tik_skaimenys) < kiekis:  # jei skaitmuo
            tik_skaimenys += simbolis  # prirašyti tik_skaimenys intamojo dešinėje

    if len(tik_skaimenys) < kiekis:
        print('Įspėjimas: grąžinamas „%s“ skaitmenų kiekis (%d) mažesnis nei prašytas (%d)'
              % (tekstas, len(tik_skaimenys), kiekis))
    return tik_skaimenys


def ar_darbo_diena(data):
    """
    Tikrina, ar nurodyta data yra darbo, ar nedarbo (savaitgalis arba šventinė). Velykų diena tik ignoruojama.
    :return: 1 = darbadienis, 0 = šventinė
    """
    # Velykoms galima žiūrėti:
    # https://pandas.pydata.org/docs/reference/api/pandas.tseries.offsets.Easter.html#pandas.tseries.offsets.Easter

    # mėnesio ir dienos sąrašas
    šventinės_dienos = [[1, 1], [2, 16], [3, 11], [5, 1], [6, 24], [7, 6], [8, 15], [11, 1], [11, 2], [12, 24]]

    try:
        df = pd.to_datetime(data, format='mixed', yearfirst=True)
    except Exception as err:
        print('Klaida: pateikti duomenys netinka datai. Išsamiau:', err)
        return None
    else:
        if isinstance(df, pd.Timestamp):  # 'Timestamp' object has no attribute 'apply'
            df = pd.Series(df)
        if isinstance(df, pd.Series) or (isinstance(df, pd.DataFrame) and len(df.columns) == 1):  # vienas stulpelis?
            # ar nėra ( (5=šeštadienis arba 6=sekmadienis) arba šventinė)
            df = df.apply(lambda x: int(not (x.weekday() in [5, 6]) or ([x.month, x.day] in šventinės_dienos)))
        elif isinstance(df, pd.DataFrame):
            print('Tikėtasi vieno duomenų stulpelio, bet rasti', len(df.columns))
        else:
            print('Netikėtas duomenų tipas:', type(df))
        return df


def pd_nuskaityti_excel(excel_rinkmena, eilutės_stulpelio_pavadinimui=1):
    """
    Bandyti nuskaityti kaip Excel dokumentą su pandas, iškart tvarkyti stulpelių pavadinimus
    :param excel_rinkmena: url arba vietinis kelias iki XLS arba XLSX
    :param eilutės_stulpelio_pavadinimui:
    :return: pandas.DataFrame() arba, jei nepavyko, None
    """
    try:
        df = pd.read_excel(excel_rinkmena)  # pirminis nuskaitymas
        bandymas = 0  # bandymų skaitliukas
        # kartoti, kol stulpelių pavadinimai bus skirtingi
        while set([st.split(':')[0] for st in list(df.columns)]) == {'Unnamed'}:  # kol visi stulpeliai bevardžiai
            # nuskaityti praleidžiant eilutės nuo viršaus; tokių tuščių eilučių buvo 2024 m. gyventojų duomenyse
            bandymas += 1
            df = pd.read_excel(excel_rinkmena, skiprows=bandymas)

        if eilutės_stulpelio_pavadinimui > 1:  # jei prašoma, kad antraštę sudarytų kelios eilutės
            eilutės_stulpeliams = list(range(bandymas, bandymas + int(eilutės_stulpelio_pavadinimui)))
            df = pd.read_excel(excel_rinkmena, header=eilutės_stulpeliams)
            valyti_pavadinimai_stulpeliams = [' '.join([re.sub(r' +', ' ', eil.strip())  # pašalina tarpus
                                                        for eil in st if eil.split(':')[0] != 'Unnamed'])
                                              # be dalių su Unnamed
                                              for st in df.columns]  # imti kiekvieną stulpelį
            df.columns = valyti_pavadinimai_stulpeliams  # pervadinti stulpelius
        else:
            # nutrinti perteklinius tarpus nuo stulpelių pavadinimų
            df.columns = [re.sub(r' +', ' ', st.strip()) for st in df.columns]
        df.dropna(axis=1, how='all', inplace=True)  # atmesti stulpelius, kuriuose nieko nėra
        return df
    except Exception as err:
        print(' Nepavyko nuskaityti', excel_rinkmena, '\n   Klaida:', err)
        return None


def pd_nuskaityti_csv(csv_rinkmena):
    """
    Funkcija padeda įkelti CSV rinkmenas, turinčias skirtingus:
     - laukų skirtukus (,;),
     - dešimtainius skirtukus (,.)
     - koduotes (windows-1257, utf-8)
    Standartinė pandas .read_csv komanda neaptinka koduotės, skirtukų automatiškai.
    """

    # Jei ne vietinė rinkmena, parsisiųsti CSV, kad nereiktų siųstis keliskart bandant skirtingus importo parametrus:
    if csv_rinkmena.split('://')[0] in ['http', 'https']:
        laikinoji_rinkmena = os.path.join(  # vardai laikinajai vietinei rinkmenai
            'data', '.laikinoji_rinkmena_' + datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S') + '.csv')
        # jei pavyks parsisisiųti, csv rinkmenos kelią pakeis į vietinį; jei nepavyks, grąžins None:
        csv_rinkmena = parsisiųsti_rinkmeną(csv_rinkmena, laikinoji_rinkmena, detaliai=False)
        sleep(1)  # palaukti sekundę po parsiuntimo
        if not csv_rinkmena:  # jei nepavyko parsisiųsti.
            return None  # išeiti grąžinant None
    else:
        laikinoji_rinkmena = None

    # Kai kurios CSV rinkmenos būna išsaugotos unikodu, bet kai kurios kitos windows-1257 koduote
    for koduotė in ['utf-8', 'windows-1257']:  # jau antroje eilutėje yra žodis „Akmenės“, kuris padeda aptikti koduotę
        try:
            with open(csv_rinkmena, mode='r', encoding=koduotė) as rinkmenos_id:
                # nuskaityti pirmas dvi eilutes - tiek užteks, nes jau antroje eilutėje yra žodis „Akmenės“
                eilutės = [next(rinkmenos_id) for _ in range(2)]

            for laukų_skirtukas in [';', ',', '\t']:  # tikrinti populiariausius laukų skirtukus paeiliui
                skirtukai_eilutėse = [eilut.count(laukų_skirtukas) for eilut in
                                      eilutės]  # suskaičiuoti skirtukus eilutėse
                # euristika: laukų skirtukų skaičius pirmoje ir antroje eilutėje bus vienodas (len(set()) == 1) ir > 0
                if len(set(skirtukai_eilutėse)) == 1 and skirtukai_eilutėse[0] > 0:
                    # dešimtainis skirtukas bus kablelis, jei tokį simbolį randa (ir jei jis nėra laukų skirtukas)
                    dešimtainis = (',' if ',' in eilutės[1].replace(laukų_skirtukas, '') else '.')
                    df = pd.read_csv(csv_rinkmena, encoding=koduotė, delimiter=laukų_skirtukas, decimal=dešimtainis)
                    if laikinoji_rinkmena and os.path.exists(laikinoji_rinkmena):  # jei buvo sukurta laikinoji rinkmena
                        os.remove(laikinoji_rinkmena)  # pašalinti laikinąją rinkmeną
                    return df
            break  # šią vietą pasiekia, jei koduotė tiko, bet netiko skirtukai
        except UnicodeDecodeError:
            pass
        except Exception as err:
            print(f' Netikėta klaida:\n ', err)
            break  # kažkas kito netikėto, bet nesusijusio su koduote ir parametrais, tad nutraukti ciklą

    # Šią vietą pasiekia tik jei jokie parametrai netiko
    print(f' Nepavyko rasti optimalių parametrų CSV rinkmenai „{csv_rinkmena}“')
    if laikinoji_rinkmena and os.path.exists(laikinoji_rinkmena):  # jei buvo sukurta laikinoji rinkmena
        os.remove(laikinoji_rinkmena)  # pašalinti laikinąją rinkmeną
    return None


def gauti_visus_sutvarkytus_duomenis(
        pasirinktas_laikotarpis=None, el_rinkinio_id='buitis', perdaryti=False, interaktyvus=True, ar_išsamiai=False
):
    """
    Pasiimti sutvarkytus duomenis arba juos surinkti ir sutvarkyti naudotojo pasirinktam arba viduriniam laikotarpiui,
    taip pat pasirinktiems regionams. Nei vienas parametras nėra būtinas.
    :param pasirinktas_laikotarpis: metai (sveikasis skaičius) arba jų sąrašas. Rekomentuojamas yra [2022].
    :param el_rinkinio_id: 'buitis' (numatyta) - buitinių vartotojų, 'verslas' - verslo vartotojų.
    :param perdaryti: False - jei įmanoma, įkelti jau sutvarkytus, o True - surinkinėti iš naujo iš pradinių
    :param interaktyvus: ar viduryje darbų naudotojui užduoti klausimui, kad jis priimtų sprendimus pasirenkant
    :param ar_išsamiai: ar rodyti paaiškinimus
    :return: pandas.DataFrame jungtiniai bendri duomenys, taip pat atskiri duomenys žodyne pagal tipą
    """

    print('\n== Duomenys ==\n')

    """
    Sukurti objektus duomenų rinkiniams valdyti
    """
    # Objektai elektros energijos suvartojimo duomenų rinkiniams
    elektra = RinkinysElektrai(rinkinio_id=el_rinkinio_id)

    # Objektas orų duomenims
    orai = RinkinysOrams()

    # Objektas demografiniams duomenims. Gyventojai savivaldybese pagal amžiaus grupes
    gyventojai = RinkinysGyventojams()

    """
    Laikotarpio pasirinkimas
    """
    # dar prieš nuskaitant/parsisunčiant pačius duomenis, rasti laikotarpį pagal skaičius nuorodose ar rinkmenų varduose
    galimi_elektros_laikotarpiai = sorted(set(elektra.metai) & set(orai.metai) & set(gyventojai.metai))  # 2021-2024 m.
    if not galimi_elektros_laikotarpiai:
        print('Be duomenų negalime tęsti.')
        return
    print('\n= Laikotarpis =')
    print('Bendras laikotarpis skirtingiems duomenų tipams yra nuo %d iki %d m.'
          % (galimi_elektros_laikotarpiai[0], galimi_elektros_laikotarpiai[-1]))
    if isinstance(pasirinktas_laikotarpis, int):  # jei naudotojas pateikė skaičių
        pasirinktas_laikotarpis = [pasirinktas_laikotarpis]  # paversti sąrašu
    if isinstance(pasirinktas_laikotarpis, list):  # jei laikotarpis yra sąrašas
        pasirinktas_laikotarpis_naudotojo = pasirinktas_laikotarpis  # kopija
        pasirinktas_laikotarpis = [m for m in pasirinktas_laikotarpis if (m in galimi_elektros_laikotarpiai)]
        if not pasirinktas_laikotarpis:
            print('Nerasta pasirinktų laikotarpių ({}) tarp prieinamų ({})'.format(
                pasirinktas_laikotarpis_naudotojo, galimi_elektros_laikotarpiai
            ))
            return
    elif len(galimi_elektros_laikotarpiai) == 1:
        pasirinktas_laikotarpis = galimi_elektros_laikotarpiai
    elif interaktyvus:  # klausti naudotojo?
        print('Jei norite, jūs galite pasirinti visą arba savitą siauresnį laikotarpį.')
        while True:  # ciklas
            try:
                pasirinkimas1 = input(
                    'Pasirinkite laikotarpio pradžią tarp {} ir {} (B arba Q - išeiti): > '.format(
                        min(galimi_elektros_laikotarpiai), max(galimi_elektros_laikotarpiai)
                    ))
                if pasirinkimas1.lower() in ['b', 'q']:
                    print('Viso gero!')
                    return None
                else:
                    pasirinktas_laikotarpis_nuo = int(pasirinkimas1)
                    if pasirinktas_laikotarpis_nuo in galimi_elektros_laikotarpiai:
                        break
            except ValueError:
                print('Įvedimas turi būti skaičius, B arba Q išėjimui')

        if pasirinktas_laikotarpis_nuo == max(galimi_elektros_laikotarpiai):
            pasirinktas_laikotarpis_iki = pasirinktas_laikotarpis_nuo
        else:
            while True:
                try:
                    pasirinkimas2 = input(
                        'Pasirinkite laikotarpio pabaigą tarp {} ir {} (B arba Q - išeiti): > '.format(
                            pasirinktas_laikotarpis_nuo, max(galimi_elektros_laikotarpiai)
                        ))
                    if pasirinkimas2.lower() in ['b', 'q', 'quit', 'quit()']:
                        print('Viso gero!')
                        return None
                    else:
                        pasirinktas_laikotarpis_iki = int(pasirinkimas2)
                        if ((pasirinktas_laikotarpis_iki in galimi_elektros_laikotarpiai) and
                                (pasirinktas_laikotarpis_iki >= pasirinktas_laikotarpis_nuo)):
                            break
                except ValueError:
                    print('Įvedimas turi būti skaičius, B arba Q išėjimui')

        pasirinktas_laikotarpis = list(range(pasirinktas_laikotarpis_nuo, pasirinktas_laikotarpis_iki + 1))

    else:
        pasirinktas_laikotarpis = int(
            sum(galimi_elektros_laikotarpiai) / len(galimi_elektros_laikotarpiai))  # vidurinis, t.y. 2022 m.

    print('Pasirinktas laikotarpis:', pasirinktas_laikotarpis)

    print('\nAtnaujinti rinkinių meta duomenys:')
    for rinkinys in [elektra, orai, gyventojai]:
        #  Atnaujinti laikotarpius objektuose ir iš naujo priskirti lenteles
        rinkinys.identifikuoti_priklausomas_rinkmenas(pasirinktas_laikotarpis)
        # Atnaujinti vietas, kur talpinama
        rinkinys.atnaujinti_rinkinio_rinkmenos_vardą()

    """
    Įkelti sutvarkytus duomenis kaip pd.DataFrame (gali būti jau įrašyti sutvarkyti, arba perrinkti ir tvarkyti dabar)
    """
    bendrieji_parametrai_tvarkymui = {'perdaryti': perdaryti, 'interaktyvus': interaktyvus, 'ar_išsamiai': ar_išsamiai}
    print(f'\n= {elektra.rinkinys.upper()} =')  # antraštės spausdinimas, nes gali būti daug veiksmo...
    df_elektra = elektra.sutvarkyti_duomenis(**bendrieji_parametrai_tvarkymui)  # pats duomenų įkėlimas / parsiuntimas
    print(f'\n= {orai.rinkinys.upper()} =')  # antraštės spausdinimas, nes gali būti daug veiksmo...
    df_orai = sutvarkyti(orai, **bendrieji_parametrai_tvarkymui)  # polimorfizmas
    print(f'\n= {gyventojai.rinkinys.upper()} =')  # antraštės spausdinimas, nes gali būti daug veiksmo...
    df_gyventojai = gyventojai.sutvarkyti_duomenis(**bendrieji_parametrai_tvarkymui)  # pats duomenų gavimas
    if any([(d is None) for d in [df_elektra, df_orai, df_gyventojai]]):  # Tikrinti, ar turime visus duomenys
        #  Kažkurių duomenų įkelti nepavyko; pvz., 2024 metų gyventojų lentelės struktūra labai skirasi nuo kitų metų
        print('Negalime tęsti neturint visų rūšių duomenų. Galbūt duomenų struktūra buvo netikėta, skiriasi tarp metų.')
        return

    print('\n= Regionai =')
    # regionų sąrašai:
    regionai_eso = df_elektra['Regionas'].unique()
    regionai_orams = df_orai['Regionas'].unique()
    regionai_demogr = df_gyventojai['Regionas'].unique()

    # regionų persidengimo patikrinimas
    if ar_išsamiai:
        regionai_eso_be_oru = sorted(set(regionai_eso) - set(regionai_orams))  # skirtumas tarp ESO ir meteo regionų
        if regionai_eso_be_oru:
            print('Įspėjimas: šie ESO regionai neturi susietų meteorologijos stočių ir orų duomenų:\n   ',
                  ', '.join(regionai_eso_be_oru))
        regionai_eso_be_demogr = sorted(set(regionai_eso) - set(regionai_demogr))
        if regionai_eso_be_demogr:
            print('Įspėjimas: šie ESO regionai neturi susietų demografinių duomenų apie gyventojus:\n   ',
                  ', '.join(regionai_eso_be_demogr))
        regionai_oru_ir_demogr_be_eso = sorted({*regionai_orams, *regionai_demogr} - set(regionai_eso))
        if regionai_oru_ir_demogr_be_eso:
            print('Įspėjimas: šios savivaldybės neturi ESO duomenų, nors turi demografinius ir orų duomenis:\n   ',
                  ', '.join(regionai_oru_ir_demogr_be_eso))
    regionai_bendri = sorted(set(regionai_eso) & set(regionai_orams) & set(regionai_demogr))
    print('\nRegionai, kuriems turime visus reikalingus duomenis:\n   ',
          ', '.join(regionai_bendri))

    # Regionų pasirinkimas
    if interaktyvus:
        pasirinkti_regionai = []
        while True:
            pasirinkimas = input('Pasirinkite regioną (VISI - visi regionai; B, Q arba nieko - baigti įvedimą): > ')
            if (pasirinkimas in regionai_bendri) and not (pasirinkimas in pasirinkti_regionai):
                pasirinkti_regionai.append(pasirinkimas)
                print(f'{pasirinkimas} regionas pridėtas.')
            elif pasirinkimas.upper() == 'VISI':
                pasirinkti_regionai = regionai_bendri
                break
            elif pasirinkimas.lower() in ['b', 'q', 'quit', 'quit()', '']:
                break
            else:
                print(' Pasirinktam „{}“ regionui neturime pilnų duomenų arba tokio nėra'.format(pasirinkimas.upper()))
                print(' Įvedimas turi būti regionas, B arba Q išėjimui. Galimi regionai:\n ',
                      ', '.join(sorted(set(regionai_bendri) - set(pasirinkti_regionai))))

    else:
        regionai_bandymui = [
            'Vilniaus', 'Vilniaus miesto', 'Vilniaus rajono',  # žiūrint, ar jie atskriti, ar kartu
            'Šiaulių', 'Ignalinos', 'Klaipėdos'
        ]
        pasirinkti_regionai = [r for r in regionai_bandymui if
                               (r in regionai_bendri)]  # bendomi regionai tarp prieinamų
    if pasirinkti_regionai:
        print('\nVisi pasirinkti regionai:\n   ', ', '.join(pasirinkti_regionai))
    else:
        print('Nepasirinkote nei vieno regiono! Nėra ką daryti toliau.')
        return None

    df_gyventojai_filtruoti = df_gyventojai[df_gyventojai['Regionas'].apply(  # atrinkti pg. regionus
        lambda x: x in pasirinkti_regionai
    )]
    # elektros ir orų duomenis nufiltruos pd.merge jungiant

    # Bendri duomenys pagal stulpelius, be NaN
    df_bendri = pd.merge(df_elektra, df_gyventojai_filtruoti, how="inner")  # kol kas tik elektra ir gyventojai
    df_bendri = pd.merge(df_bendri, df_orai, how="inner")  # prijungti orų duomenis
    print('\nSkirtingų tipų duomenys sėkmningai apjungti!\n')

    return df_bendri


if __name__ == '__main__':
    df_bendrieji = gauti_visus_sutvarkytus_duomenis(perdaryti=False, interaktyvus=True, ar_išsamiai=True)
