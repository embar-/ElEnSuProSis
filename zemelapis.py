import os
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns
from collections import defaultdict
from meteo_lt import stotys_ir_regionai  # regionų koordintėms gauti


def žemėlapis(duomenys=None, skersmuo=None, spalva=None, stilius=None,
              pavadinimas=None, legendos_pavad=None, agg_fja='sum',
              rodyti=True, kontūro_rinkmena='data/Lietuvos_siena.csv',
              **papildomi_sns_parametrai):
    """
    Nupiešia Lietuvos kontūro žemėlapį su pasirinktais duomenimis.
    Funkcija veikia netgi be jokių parametrų - tada nubraižo tik kontūrą.
    :param duomenys: None arba pandas.DataFrame lentelė, kurioje turi būti kintamasis 'Regionas'.
    Palaikoma maždaug 20 regionų, kuriuose yra meteoroligijos stotys,
    nes pagal jas žymima regiono vieta; regionai daugmaž atitinka rajonų savivaldybes,
    bet kartais nesutampa su savivaldybių centrais
    (pvz., Vilkaviškio regiono taškas bus Kybartuose, nes būtent ten yra meteorologijos stotis);
    regionus reikia nurodyti kilmininko linksniu, pvz. ['Kauno', 'Klaipėdos', 'Panevėžio', 'Šiaulių', 'Vilniaus']

    Pavyzdys:

    žemėlapis(
        ['Kauno', 'Klaipėdos', 'Panevėžio', 'Šiaulių', 'Vilniaus'],
        skersmuo=[4, 4, 3, 3, 6],
        )

    :param skersmuo: regioną atitinkančio skrituliuko dydis kaip skaičius arba kintamjo vardas duomenyse jiems paimti
    :param spalva: regioną atitinkančio skrituliuko spalva arba kintamjo vardas duomenyse jiems paimti
    :param stilius: regioną atitinkančio skrituliuko stilius arba kintamjo vardas duomenyse jiems paimti
    :param pavadinimas: žemėlapio pavadinimas
    :param legendos_pavad: legendos pavadinimas
    :param agg_fja: agregavimo funkcija, kuri naudodojama tuo atveju, jei regionas paminimas kelis kartus
    :param papildomi_sns_parametrai: papildomi seaborn parametrai
    :param rodyti: [True|False] ar pabaigoje įvykti plt.show() galutiniam atvaizdavimui (numatyta taip/True)
    :param kontūro_rinkmena: kelias iki CSV su Lietuvos sienos kontūro koordinatėmis; su stulpeliais 'ilguma', 'platuma'
    """

    # Kintamieji
    if not (duomenys is None):  # ar pateikti duomenys?
        if isinstance(duomenys, pd.DataFrame):
            duomenys = duomenys.copy()  # atsargumo dėlei, kad nepakeistų aukštesnėje f-joje
        else:  # jei nėra pd.DataFrame
            try:
                duomenys = pd.DataFrame(duomenys)  # bandyti konvertuoti į pd.DataFrame
            except Exception as err:
                print('Pateikti duomenys nebuvo pandas.DataFrame lentelė ir nepavyko jų konvertuoti:', err)
                return

        """ skersmuo, spalva, stilius """
        # Patiktinti
        kintamieji_su_pavadinimu = [kint for kint in [skersmuo, spalva, stilius] if isinstance(kint, str)]  # tekstiniai
        if any([kint for kint in kintamieji_su_pavadinimu if not (kint in duomenys.columns)]):
            raise Exception('Duomenyse nėra nurodyto(-ų) kintamojo(-ųjų).')

        """ Regionai """

        if not ('Regionas' in duomenys.columns) and len(duomenys.columns) > 0:  # Jei nėra 'Regionas', bet yra kt.
            if (duomenys.columns[0] == 0) and (type(duomenys[0][0]) is str):  # jei stulpelis bevardis, o jame tekstas
                duomenys = duomenys.rename(columns={0: 'Regionas'})
            else:
                print('Duomenyse nepavyko rasti „Regionas“ kintamojo, o pirmame stulpelyje buvo ne tekstas')
                return

        # Regionų koordinatės
        platuma, ilguma, regionai_be_vietos = gauti_koordinates_regionams(duomenys['Regionas'])

        # Regionus be vietos sugrupuoti ir pervadinti
        if regionai_be_vietos:
            regionų_be_vietos_atitikmenys = {r: '<BE VIETOS>' for r in regionai_be_vietos}
            duomenys['Regionas'] = duomenys[['Regionas']].replace(regionų_be_vietos_atitikmenys)  # pervadinti
            duomenys = agreguoti_pagal_regioną(duomenys, agg_fja, [skersmuo, spalva, stilius])  # agreguoti
            # iš naujo priskirtis koordinates
            platuma, ilguma, _ = gauti_koordinates_regionams(duomenys['Regionas'])

        # Regionų patikrinimas:
        if len(platuma) and all([(x is None) for x in platuma]):  # jei visos platumos tuščios
            print('Duomenyse nerasta nei vienos tinkamos „Regionas“ kintamojo reikšmės.')
        else:
            if len(duomenys) > len(duomenys['Regionas'].unique()):
                print('Kai kurie regionai pasikartojama. Agreguojama...')
                duomenys = agreguoti_pagal_regioną(duomenys, agg_fja, [skersmuo, spalva, stilius])  # agreguoti
                # iš naujo priskirtis koordinates
                platuma, ilguma, _ = gauti_koordinates_regionams(duomenys['Regionas'])

        """ skersmuo, spalva, stilius jau turint regionus"""

        # jei df turi tik dar vieną stulpelį (be regiono) - automatiškai jį naudoti dydžiui
        if len(duomenys.columns) == 2:
            skersmuo = duomenys.columns[1] if duomenys.columns[0] == 'Regionas' else duomenys.columns[0]

        # jei nurodytas tik vienas iš šių: spalva arba arba skersmuo, tai panaudoti ir kitam
        if (skersmuo is None) and (isinstance(spalva, str)):
            skersmuo = spalva
        if (spalva is None) and (isinstance(skersmuo, str)):
            spalva = skersmuo

    else:
        platuma, ilguma, regionai_be_vietos = None, None, None  # nereikės jų

    kintamieji_su_pavadinimu = [kint for kint in [skersmuo, spalva, stilius] if isinstance(kint, str)]  # tekstiniai

    """ 
    Visos Lietuvos teritorijos kontūras
    """

    ar_pavyko_nupiešti_kontūrą = False  # kol kas kontūro nėra; kai nupieš, pakeisim į True
    if os.path.isfile(kontūro_rinkmena):
        # print('Lietuvos kontūras rastas:', kontūro_rinkmena)
        try:
            kontūras = pd.read_csv(kontūro_rinkmena)
            if ('platuma' in kontūras.columns) and ('ilguma' in kontūras.columns):
                kontūras.plot('ilguma', 'platuma', c='lightgray',  # sienos linija pagal koordinates, šviesiai pilka
                              label='', xlabel='', legend=False,  # be užrašų
                              xticks=[], yticks=[],
                              )
                plt.axis(False)
                # ax1.axis('equal')  # turėtų niekada neištampyti žemėlapio, bet nepadeda
                ar_pavyko_nupiešti_kontūrą = True
            else:
                print('Tikėtasi, kad {} turės stulpelius „platuma“ ir „ilguma“'.format(kontūro_rinkmena))
                print('Rasti stulpeleliai:', list(kontūras.columns))
        except Exception as err:
            print('Nepavyko nupiešti kontūro:', err)
    elif duomenys is None:
        print('Nėra ką toliau daryti, nes nepateikėte nei duomenų, nei pavyko rasti kontūrą ', kontūro_rinkmena)
        return

    if duomenys is None:
        if ar_pavyko_nupiešti_kontūrą:
            if rodyti:  # ar naudotojas prašo atvaizduoti? gali nenorėti, jei tęs piešimą ant viršaus su kitomis f-jomis
                plt.show()  # atvaizduoti
        else:
            print('Nėra ką toliau daryti, nes nepateikėte duomenų. Nurodykite duomenys=pandas.DataFrame()')
        return

    # „Nepažymėti regionai“ bus parodyti, bet už Lietuvos ribų:
    if regionai_be_vietos:
        plt.text(26.3, 54.8, 'Kiti:', horizontalalignment='center', verticalalignment='bottom')

    # Regionų taškai/skrituliukai
    ax = sns.scatterplot(
        data=duomenys,
        x=ilguma, y=platuma,  # koordinatės
        size=skersmuo, sizes=(20, 500), hue=spalva, style=stilius,  # skrituliukų atvaizdavimo ypatybės
        **papildomi_sns_parametrai  # kiti kintamieji
    )

    # legendos pavadinimas
    if legendos_pavad:
        plt.legend(title=legendos_pavad)
    elif isinstance(skersmuo, str) and not any([spalva, stilius]):
        plt.legend(title=skersmuo.replace('_', ' '))
    elif isinstance(spalva, str) and not any([skersmuo, stilius]):
        plt.legend(title=spalva.replace('_', ' '))
    elif isinstance(stilius, str) and not any([skersmuo, spalva]):
        plt.legend(title=stilius.replace('_', ' '))

    # legendos vieta
    if len(kintamieji_su_pavadinimu) < 2:  # nėra ar tik 1 duomenų kintamasis legendoje
        plt.legend(loc='lower left')  # legendos vieta apačioje kairėje
    else:
        if (all([len(k) < 10 for k in kintamieji_su_pavadinimu]) or  # trumpi pavadinimai užima mažiau vietos
                len(duomenys['Regionas'].unique()) < 6):
            sns.move_legend(
                ax, "lower left", bbox_to_anchor=(-0.14, -0.14),  # nustumti dar papildomai į kairę
                ncol=len(kintamieji_su_pavadinimu),  # stulpelių skaičius
                frameon=False  # be rėmelio pusiau skaidraus fono
            )
        elif all([len(k) < 15 for k in kintamieji_su_pavadinimu]):  # vidutinio ilgio
            sns.move_legend(  # gerai žiūrisi su gyventojais pagal amžių
                # ax, 'lower left', bbox_to_anchor=(-0.1, -0.15),  # nustumti dar papildomai į kairę
                ax, 'center left', bbox_to_anchor=(-0.15, 0.54),  # nustumti dar papildomai į kairę
                # ax, "lower left", bbox_to_anchor=(-0.2, 0.2),  # nustumti dar papildomai į kairę
                frameon=False  # be rėmelio pusiau skaidraus fono
            )
        else:  # didesnės lentelės
            sns.move_legend(
                ax, 'center left', bbox_to_anchor=(-0.2, 0.1),  # nustumti dar papildomai į kairę
                # ax, "lower left", bbox_to_anchor=(-0.2, 0.2),  # nustumti dar papildomai į kairę
                frameon=False  # be rėmelio pusiau skaidraus fono
            )

    if pavadinimas:
        plt.title(pavadinimas)

    # ax.set_aspect('equal', 'box')  # niekada neištampyti žemėlapio
    # ax.axis('equal') # niekada neištampyti žemėlapio

    plt.tight_layout()  # nepalikti didelių paraščių

    if rodyti:  # ar naudotojas prašo atvaizduoti? gali nenorėti, jei tęs piešimą ant viršaus su kitomis funkcijomis
        plt.show()  # atvaizduoti


def agreguoti_pagal_regioną(df, agg_fja='sum', agg_kintamieji=None):
    """
    Agreguoti duomenis, esančius pandas.DataFrame lentelėje, pagal regioną
    :param df: pandas.DataFrame lentelė
    :param agg_fja: agregavimo funkcija, pvz., 'sum', 'max'
    :param agg_kintamieji: sąrašas skaitinių kintamųjų vardų, kuriuos agreguoti, bet neleis agreguoti datų
    :return:
    """
    if agg_kintamieji is None:  # automatiškai nustatyti
        agg_kintamieji = [st for st in df.columns if (df[st].dtype.name in ['int32', 'int64', 'float64'])]  # skaičiai
        agg_kintamieji = list(set(agg_kintamieji) - {'Metai', 'Mėnuo', 'Sav_diena', 'Sav. diena' 'Valanda'})  # be datų
    else:
        if isinstance(agg_kintamieji, str):  # jei kaip tekstas tik vienas kintamasis
            agg_kintamieji = [agg_kintamieji]  # paversti sąrašu
        elif not isinstance(agg_kintamieji, list):
            raise Exception('Agregavimui ')
        agg_kintamieji = [k for k in agg_kintamieji if (isinstance(k, str) and k in df.columns)]  # tekstiniai
        agg_kintamieji = list(set(agg_kintamieji))  # unikalūs
    df = df.groupby('Regionas')[agg_kintamieji].agg(agg_fja).reset_index()  # agreguoti
    return df


def gauti_koordinates_regionams(regionas):
    regionai_df = stotys_ir_regionai(tyliai=True)  # pandas.DataFrame su stočių koordinatėmis ir regionais
    regionai_df = regionai_df.set_index('Regionas')
    regionai_df_ = regionai_df.transpose()  # transponuoti: regionai tampa stulpeliais
    # Papildomai išskirti Vilnių ir Vilniaus miestą, nes tai du skirtingi ESO regionai
    if 'Vilniaus' in regionai_df_.columns:  # jei yra toks stulpelis 'Vilniaus'
        vilnius = regionai_df_[['Vilniaus']]
        for priedas in [' miesto', ' rajono']:
            if ('Vilniaus' + priedas) not in regionai_df_.columns:
                vilnius_ = vilnius.copy().rename(columns={'Vilniaus': 'Vilniaus' + priedas})
                regionai_df_ = pd.concat([regionai_df_, vilnius_], axis='columns')
    regionai_žodynas = regionai_df_.to_dict(into=defaultdict(list))  # konvertuoti į žodyną
    # regionai be koordinačių
    kiti_regionai = sorted(
        set([r for r in regionas if not (r in regionai_žodynas)]))  # unikalūs regionai be koordinačių
    NaNplat = 54.7  # platuma tiems, kurie neturi koordinatės
    NaNilgu = 26.3  # ilguma tiems, kurie neturi koordinatės
    # rasti kiekvieno regiono koordinates žodyne sukant for ciklą
    platuma = [(regionai_žodynas[r]['latitude'] if r in regionai_žodynas else NaNplat) for r in regionas]
    ilguma = [(regionai_žodynas[r]['longitude'] if r in regionai_žodynas else NaNilgu) for r in regionas]
    if kiti_regionai and (kiti_regionai != ['<BE VIETOS>']):
        print(' Įspėjimas: neradome koordinačių regionams, kurie neturi meteorologijos stočių:', kiti_regionai)
    return platuma, ilguma, kiti_regionai
