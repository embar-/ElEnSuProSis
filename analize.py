import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mpl_dates
from sklearn.preprocessing import StandardScaler  # duomenų transformacijoms, standartizavimui; reikalingas scikit-learn
import seaborn as sns
import duomenys
from zemelapis import žemėlapis

"""
Elektros, demografiniai ir orų duomenų analizė
"""


def analizuoti_jungtinius_duomenis(el_rinkinio_id='buitis', interaktyvus=True,
                                   laikotarpis_orams_ir_gyventojams_nebeanalizuoti=None):
    """
    Analizuoti interaktyviai surinktus arba įkeltus jungtinius elektros, meteorologinius ir demografinius duomenis.
    :param el_rinkinio_id: 'buitis' (numatyta) - buitinių elektros vartotojų, 'verslas' - verslo elektros vartotojų
    :param interaktyvus: užduoti klausimus naudotojui ir leisti jam pačiam pasirinkti
    :param laikotarpis_orams_ir_gyventojams_nebeanalizuoti: meteorologinių ir demografinių duomenų analizę praleisti,
    jei naudotojo pasirinktas laikotarpis sutampa su nurodytuoju; tai padės išvengti tų pačių duomenų analizavimo, nors
    elektros duomenų rinkinys būtų pasikeitęs.
    :return: grąžina metus kaip tekstą,
    """

    # atsiklausti, ar vykdyti
    if interaktyvus:
        while True:  # klausti, kol pasirinks TAIP arba NE
            pasirinkimas = input(
                '\nAr norite analizuoti elektros ({}), orų ir gyventojų duomenis '.format(el_rinkinio_id.upper()) +
                'pasirinkdami regionus bei laikotarpį? \nĮveskite [TAIP] arba NE: > ')
            if pasirinkimas.upper() in ['N', 'NE']:
                return None
            elif pasirinkimas.upper() in ['', 'T', 'TAIP']:
                break

    # Jungtiniai elektros, demografiniai ir orų duomenys
    df = duomenys.gauti_visus_sutvarkytus_duomenis(
        el_rinkinio_id=el_rinkinio_id, perdaryti=False, interaktyvus=interaktyvus, ar_išsamiai=True
    )
    if df is None:  # jei nepavyko surinkti ar įkelti jungtinių duomenų
        return None  # išeiti be papildomų paaiškinimų; klaidos bus paaiškintos gauti_visus_sutvarkytus_duomenis f-joje

    print("Analizuojami duomenys...")

    # elektra
    pavadinimo_priedėlis = ' %s m. (%s)' % (metai_žodžiu(df['Metai']), el_rinkinio_id)
    šalies_abonentai_ir_vidutinis_suvartojimas(df, priedėlis=pavadinimo_priedėlis)
    suvartojimo_kitimas_paroje_pagal_regionus(df, priedėlis=pavadinimo_priedėlis)

    if df['Metai'].unique().tolist() == laikotarpis_orams_ir_gyventojams_nebeanalizuoti:  # jei nesikartoja laikotarpis
        print('Praleidžiama orų ir gyventojų analizė, nes šiam laikotarpiui ji jau atlikta')
    else:
        # demografija
        analizuoti_gyventojus(df)

        # orai
        analizuoti_orus(df)

    print("\n- - - - -")
    return df['Metai'].unique().tolist()  # grąžinti metus, kurie buvo analizuoti


""" Demografiniai duomenys """


def analizuoti_gyventojus(df_gyventojai):
    """
    Nupiešti žemėlapiuose gyventojų pasiskirstymą pagal amžiaus grupes.
    :param df_gyventojai: pandas.DataFrame lentelė, kurią galite sukurti įvykdę, pvz.,
    df_gyventojai = duomenys.RinkinysGyventojams(2022).sutvarkyti_duomenis(perdaryti=False, interaktyvus=True)
    """

    if not tikrinti_df(
            df_gyventojai,
            [
                'Regionas',
                'Gyventojai 0–6 m. (%)',
                'Gyventojai 7–17 m. (%)',
                'Gyventojai 18-59 m. (%)',
                'Gyventojai 60 m. + (%)',
            ]
    ):
        return

    metai_str = metai_žodžiu(df_gyventojai['Metai'])
    pavadinimas = 'Gyventojų pasiskirstymas pagal amžių {} m.'.format(metai_str)
    žemėlapis(  # pervadinti trumpesniais pavadinimais atvaizdavimui glaustesnėse legendose
        df_gyventojai.rename(columns={'Gyventojai 60 m. + (%)': '60+ m., %', 'Gyventojai 18-59 m. (%)': '18-59 m., %'}),
        '18-59 m., %', '60+ m., %', pavadinimas=pavadinimas, legendos_pavad='Amžius',
        agg_fja='median',  # mediana naudojama regionams be vietos agreguoti
    )
    žemėlapis(  # pervadinti trumpesniais pavadinimais atvaizdavimui glaustesnėse legendose
        df_gyventojai.rename(columns={'Gyventojai 0–6 m. (%)': '0-6 m., %', 'Gyventojai 7–17 m. (%)': '7-17 m., %'}),
        '7-17 m., %', '0-6 m., %', pavadinimas=pavadinimas, legendos_pavad='Amžius',
        agg_fja='median',  # mediana naudojama regionams be vietos agreguoti
    )


""" Meteorologiniai duomenys """


def analizuoti_orus(df_orai):
    """
    Nupiešti žemėlapiuose vidutinius orus regione
    :param df_orai: pandas.DataFrame lentelė su kintamaisiais 'Regionas', 'Vėjo greitis (m/s)', 'Temperarūra (C)',
    'Drėgnis (%)', 'Slėgis (hPa)'
    """

    if not tikrinti_df(
            df_orai,
            ['Regionas', 'Vėjo greitis (m/s)', 'Temperarūra (C)', 'Drėgnis (%)', 'Slėgis (hPa)']
    ):
        return

    metai_str = metai_žodžiu(df_orai['Metai'])
    žemėlapis(df_orai, 'Vėjo greitis (m/s)', 'Temperarūra (C)',
              agg_fja='mean', pavadinimas='Vidutinai orai regione {} m.'.format(metai_str))
    žemėlapis(df_orai, 'Drėgnis (%)', 'Slėgis (hPa)',
              agg_fja='mean', pavadinimas='Vidutinai orai regione {} m.'.format(metai_str))


"""
Automatizuotų elektros abonentų ir jų energijos suvartojimo aprašomoji statistinė analizė
"""


def analizuoti_elektros_duomenis(rinkinio_id='buitis', metai=2022):
    """
    Automatizuotų elektros abonentų energijos suvartojimo analizės pagrindinė funkcija.
    Kviečiant per ją, elektros duomenys surenkami per visą laikotarpį, o ne imami iš jungtinių (su orais ir gyventojais)
    duomenų. Jei norėtumėte analizuoti elektros duomenis su jungtiniais duomenimis, paduokite juos konkrečioms žemesnio
    lygio elektros duomenų analizės funkcijoms. Pirmuoju etapu apžvelgiamas abonentų skaičiaus ir elektros suvartojimo
    per visą prieinamą laikotarpį kitimas bendrai Lietuvoje. Antruoju etapu analizuojamas tik siauresnis vienerių metų
    laikotarpis, bet išsamiau pagal Lietuvos regionus.
    :param rinkinio_id: 'buitis' – buitinių vartotojų (numatyta), 'verslas' - verslo vartotojų
    :param metai: skaičius nuo 2021 iki šių metų, numatyti 2022 m.
    """

    # išvestiniai bendri kintamieji
    priedėlis = f' ({rinkinio_id})' if rinkinio_id else ''  # pavadinimų priedėlis

    """ Iš pradžių analizuoti visą laikotarpį """
    # Elektros suvavrtojimo duomenys er visą laikotarpį
    elektra = duomenys.RinkinysElektrai(rinkinio_id=rinkinio_id)  # duomenų objektas: elektra
    elektra.atnaujinti_rinkinio_rinkmenos_vardą()  # vietoj data/elektra_buitis.csv būtų su metų priesaga
    df_elektra = elektra.sutvarkyti_duomenis(perdaryti=False, interaktyvus=True, ar_išsamiai=False)  # gauti sutvartytus

    if df_elektra is None:
        print("Elektros suvartojimo duomenų rinkinyje nebuvo duomenų")
        return

    # Per visą laikotarpį bendra Lietuvos analizė: abonentų skaičius ir vidutinio suvartojimo kitimas
    šalies_abonentai_ir_vidutinis_suvartojimas(df_elektra, priedėlis=priedėlis)

    """ Analizuoti tik pasirinktus metus """

    if metai in df_elektra['Metai'].unique():  # ar turime 2022 m. duomenis? šių metų duomenys gausiausi
        # Duomenys atrenkami tik 2022 metų
        df_elektra1m = df_elektra[df_elektra['Metai'] == metai]
    else:  # bandyti pakartotinai, bet imti iš pat pradžių tik norimus metus
        df_elektra1m = duomenys.RinkinysElektrai(rinkinio_id, metai)  # duomenų objektas: elektra 2022 m.
        df_elektra1m.atnaujinti_rinkinio_rinkmenos_vardą()  # vietoj data/elektra_buitis.csv būtų su metų priesaga
        df_elektra1m = elektra.sutvarkyti_duomenis(perdaryti=False, interaktyvus=False, ar_išsamiai=False)
        if df_elektra1m is None:
            return  # kažkokia klaida, ji greičiausiai jau bus aprašyta

    # Lyginti elektros suvartojimo kitimą paros eigote tarp mėnesių.
    suvartojimo_kitimas_paroje_tarp_mėnesių(  # Visa Lietuva, parinkti mėnesiai įvertinti, ar laiko juostos tvarkingos
        df_elektra1m, mėnesiai=[2, 4, 9, 11], priedėlis=priedėlis
    )
    suvartojimo_kitimas_paroje_tarp_mėnesių(  # Visa Lietuva, atskiri mėnesiai
        df_elektra1m, mėnesiai=[3, 6, 9, 12], priedėlis=priedėlis
    )

    # Regionų suvartojimo kitimo laike grafikai ir žemėlapiai
    regionų_abonentai_ir_vidutinis_suvartojimas(df_elektra1m, priedėlis=' {} m.{}'.format(metai, priedėlis))


def šalies_abonentai_ir_vidutinis_suvartojimas(df, priedėlis=''):
    """
    Grafikai apie elektros automatizuotus abonentus ir jų elektros vartojimą imant visą Lietuvą kaip visumą
    :param df: pandas.DataFrame lentelė su elektros suvartojimo duomenimis, kuriuos galima gauti iškvietus
    df = duomenys.RinkinysElektrai().sutvarkyti_duomenis()
    :param priedėlis: papildomas prierašas paveikslėlio pavadinime, pvz., ' (buitiniai)', ' verslo 2022 m.'
    """

    Lietuva_per_valandą = df.groupby(
        ['Data_laikas', 'Data', 'Valanda']  # Išlaikyti datas ir valandas kintamuosius dar vėlesniam grupavimui
    )[['Data_laikas', 'Abonentai', 'Suvartojimas (kWh/val)']].agg(  # atrenkami stulpeliai
        {'Abonentai': 'sum', 'Suvartojimas (kWh/val)': 'sum'}  # agregavimo f-jos priklausomai nuo kintamojo
    ).reset_index()  # datų ir valandų informacija iš indeksų grįžta į įprastus stulpelius

    # Pruošti analizei pagal dienas
    Lietuva_per_dieną = Lietuva_per_valandą.groupby(['Data'])[['Abonentai', 'Suvartojimas (kWh/val)', 'Valanda']].agg(
        {'Abonentai': 'max', 'Suvartojimas (kWh/val)': 'sum', 'Valanda': 'count'}
    ).rename(columns={'Suvartojimas (kWh/val)': 'Elektra_kWh_per_d'}).reset_index()
    # aptikti dienas, kurių informacija nepilna; bet leisti 23 valandas turinčias dienas dėl žiemos>vasaros laiko sukimo
    nepilnos_dienos = Lietuva_per_dieną['Data'][Lietuva_per_dieną['Valanda'] < 23].to_list()  # arba < 24
    if nepilnos_dienos:
        print('Kai kuriomis dienomis informacija nepilna:', nepilnos_dienos)
        Lietuva_per_dieną = Lietuva_per_dieną[Lietuva_per_dieną['Valanda'] >= 23].reset_index()  # atrinkti pilnesnes d.
    # Apskaičiuoti vieno abonento vidutinį suvartojimą
    Lietuva_per_dieną['Elektros energijos kiekis (kWh per parą)'] = (
            Lietuva_per_dieną['Elektra_kWh_per_d'] / Lietuva_per_dieną['Abonentai']
    )

    # Abonentų skaičiaus kitimas laike
    plt.figure(figsize=(9, 6))  # platesnis paveiksliukas nei standartinis
    atvaizduoti_kitimą_per_metus(
        df=Lietuva_per_dieną, x='Data', y='Abonentai',
        pavadinimas=f'Lietuvos automatizuotų elektros abonentų skaičius kitimas{priedėlis}',
        rodyti=False
    )
    plt.ylabel('Abonentų skaičius')
    plt.show()  # atvavizduoti; 2021-03-28 4 val ryto matyti abonentų šuolis nesutvarkytuose duomenyse

    # Vidutinio abonento elektros suvartojimas
    plt.figure(figsize=(9, 6))  # platesnis paveiksliukas nei standartinis
    atvaizduoti_kitimą_per_metus(  #
        df=Lietuva_per_dieną, x='Data', y='Elektros energijos kiekis (kWh per parą)',
        pavadinimas=f'Vidutinio automatizuoto abonento elektros suvartojimo Lietuvoje kitimas{priedėlis}'
    )


def regionų_abonentai_ir_vidutinis_suvartojimas(df, priedėlis=''):
    """
    Grafikai apie elektros abonentus ir jų elektros vartojimą Lietuvos regionuose
    :param df: pandas.DataFrame lentelė su elektros suvartojimo duomenimis, kuriuos galima gauti iškvietus
    df = duomenys.RinkinysElektrai().sutvarkyti_duomenis()
    :param priedėlis: papildomas prierašas paveikslėlio pavadinime, pvz., ' (buitiniai)', ' verslo 2022 m.'
    """

    # Lyginti elektros suvartojimo kitimą paros eigoje tarp regionų.
    suvartojimo_kitimas_paroje_pagal_regionus(df, priedėlis=priedėlis)  # Atskiri regionai, bendrai metai

    kombinuoti_žemėlapius = True
    if kombinuoti_žemėlapius:
        žemėlapis(
            df.rename(columns={'Vid. reg. ab. suvartojimas (kWh/val)': 'Suvartojimas kWh / val.'}),
            'Abonentai', 'Suvartojimas kWh / val.',
            pavadinimas='Automatizuoti elektros vartotojai{}'.format(priedėlis),
            agg_fja={'Suvartojimas kWh / val.': 'median', 'Abonentai': 'max'}
        )
    else:
        žemėlapis(
            df, 'Abonentai', agg_fja='max',
            # pavadinimo gale pridedu tarpų ir NBSP, kad labiau pastumtų jį į kairę; plt.tight_layout() iškreipia žemėl.
            pavadinimas='Didžiausias autom. elektros vartotojų skaičius regione{}      '.format(priedėlis)
        )
        žemėlapis(
            df, 'Vid. reg. ab. suvartojimas (kWh/val)',
            # pavadinimo gale pridedu tarpų ir NBSP, kad labiau pastumtų jį į kairę; plt.tight_layout() iškreipia žemėl.
            pavadinimas=f'Autom. vartotojo vidutinis el. energijos suvartojimas{priedėlis} (mediana)              ',
            legendos_pavad='Suvartojimas\nkWh / val.', agg_fja='median'
        )


def suvartojimo_kitimas_paroje_tarp_mėnesių(df, mėnesiai=None, pavadinimas=None, priedėlis='', rodyti=True):
    """
    Funkcija skirta vizualizualiam vidutinio elektros suvartojimo kitimą paros eigoje palyginimui tarp mėnesių.
    Jei laiko juostos teisingos, tai suvartojimas prieš ir po vasaros/žiemos laiko pakeitimo turėtų būti panašus,
    t.y. vasario ir balandžio, taip pat rugsėjo ir lapkričio.
    Jei laikas yra UTC (o ne vietinis), tada matysis ryškus vienos valandos persislinkimas.
    :param df: pandas.DataFrame lentelė su kintamaisiais „Mėnuo“, „Valanda“, „Suvartojimas (kWh/val)“
    :param mėnesiai: mėnesių numerių sąrašas arba None (tada imami [2, 4, 9, 11] mėnesiai).
    :param pavadinimas: paveiksliuko antraštė, pasirinktinai.
    :param priedėlis: jei pavadinimas nenurodomas, jis kuriamas automatiškai su nurodytu priedėliu (pvz., „buitinių“)
    :param rodyti: ar parodyti paveiksliuką
    """

    # Pradiniai kintamieji
    if mėnesiai is None:
        mėnesiai = [2, 4, 9, 11]  # du pavasario ir du rudens mėnesiai prieš ir po vasaros/žiemos laiko keitimo
    elif isinstance(mėnesiai, int):
        mėnesiai = [mėnesiai]
    elif not isinstance(mėnesiai, list):
        print('Mėnesiai turi būti sveikųjų skaičių sąrašas, skaičius arba None')
        return
    if not tikrinti_df(df, ['Mėnuo', 'Valanda', 'Suvartojimas (kWh/val)']):
        return
    el_v_val = df.groupby(['Mėnuo', 'Valanda']).agg({'Suvartojimas (kWh/val)': 'mean'}).reset_index()

    # Grafikas
    for mėnuo in mėnesiai:
        df_mėnesio = el_v_val[el_v_val['Mėnuo'] == mėnuo]
        mėnuo_žodžiu = mėnesio_pavadinimas(mėnuo)
        # Reikia dvigubų laužtinių skliaustų, antraip bus klaida:
        # ValueError: Expected a 2-dimensional container but got <class 'pandas.core.series.Series'> instead.
        st = StandardScaler().fit_transform(df_mėnesio[['Suvartojimas (kWh/val)']])
        plt.plot(df_mėnesio['Valanda'], st, label=mėnuo_žodžiu)

    if pavadinimas is None:
        metai_str = [str(m) for m in sorted(df['Metai'].unique())]
        plt.title(f'Automatizuoto elektros abonento energijos vidutinio suvartojimo\n'
                  'kitimas paros eigoje {} m. Lietuvoje pagal mėnesius{}'.format(', '.join(metai_str), priedėlis))
    elif pavadinimas:
        plt.title(pavadinimas)
    plt.xlabel('Valanda')
    plt.ylabel('Standartizuotas abonento el. suvartojimas')
    plt.grid(True)  # tinklelis
    plt.legend(title='Mėnuo')
    plt.tight_layout()  # apkirpti nuo tuščių vietų ir išplėsti matomas paveviksliuko dalis, kad viskas tilptų
    if rodyti:  # ar atvaizduoti kaip galutinai išbaigtą paveiksliuką?
        plt.show()


def suvartojimo_kitimas_paroje_pagal_regionus(df, pavadinimas=None, priedėlis='', rodyti=True):
    """
    Funkcija skirta vizualizualiam vidutinio elektros suvartojimo kitimo paros eigoje palyginimui tarp regionų.
    :param df: pandas.DataFrame lentelė su kintamaisiais „Regionas“, „Valanda“, „Suvartojimas (kWh/val)“
    :param pavadinimas: paveiksliuko antraštė, pasirinktinai.
    :param priedėlis: jei pavadinimas nenurodomas, jis kuriamas automatiškai su nurodytu priedėliu (pvz., „buitinių“)
    :param rodyti: ar parodyti paveiksliuką
    """

    stiliai_linijoms = ['-', '--', ':', '-.', '.']  # vėliau stilius keisimas kas 11 linijų, nes tiek st. spalvų
    el_v_val = df.groupby(['Valanda', 'Regionas']).agg({'Suvartojimas (kWh/val)': 'mean'}).reset_index()
    unikalus_regionai = df['Regionas'].unique()
    if len(unikalus_regionai) > 40:
        plt.figure(figsize=(12, 6))  # daug platesnis paveiksliukas nei standartinis - ypač daug vietos užims legenda
    elif len(unikalus_regionai) > 10:
        plt.figure(figsize=(10, 6))  # platesnis paveiksliukas nei standartinis - daug vietos užims legenda
    for i, regionas in enumerate(unikalus_regionai):
        df_regiono = el_v_val[el_v_val['Regionas'] == regionas]
        linijos_stilius = stiliai_linijoms[int(i / 10) % len(stiliai_linijoms)]
        # žemiau naudoti dvigubus laužtinius skliaustus, antraip
        # ValueError: Expected a 2-dimensional container but got <class 'pandas.core.series.Series'> instead.
        st = StandardScaler().fit_transform(df_regiono[['Suvartojimas (kWh/val)']])
        plt.plot(
            df_regiono['Valanda'], st, linijos_stilius, label=regionas
        )
    plt.grid(True)
    plt.xlabel('Valanda')
    plt.ylabel('Standartizuotas abonento el. suvartojimas')
    plt.legend(title='Regionas')
    if len(unikalus_regionai) > 10:
        sns.move_legend(  # perkelti legendą
            plt.gca(), "upper left", bbox_to_anchor=(1, 1),  # viršuje dešinėje už paveikslo
            ncol=int(len(unikalus_regionai) / 20) + 1,  # stulpelių skaičius
            frameon=False  # be rėmelio pusiau skaidraus fono
        )
    if pavadinimas is None:
        plt.title('Elektros energijos suvartojimo kitimas\n '
                  'paros eigoje skirtinguose regionuose{}'.format(priedėlis))
    elif pavadinimas:
        plt.title(pavadinimas)
    plt.tight_layout()  # apkirpti nuo tuščių vietų ir išplėsti matomas paveviksliuko dalis, kad viskas tilptų
    if rodyti:  # ar atvaizduoti kaip galutinai išbaigtą paveiksliuką?
        plt.show()


"""
Bendrieji įrankiai
"""


def atvaizduoti_kitimą_per_metus(df, x='Data', y=None, pavadinimas=None, rodyti=True):
    """
    Apvalkalas grafiko piešimui su Matplotlib ir Seaborn, kur x ašyje atidamas laikas metai-mėnuo
    :param df: pandas.DataFrame lentelė
    :param x: df stulpelio pavadinimas, kuriame yra data (numatyta "Data")
    :param y: df stulpelio pavadinimas, kuriame yra norimi atvaizduoti duomenys
    :param pavadinimas: pasirinktinai paveikslėlio antraštė
    :param rodyti: ar parodyti paveiksliuką
    :return: pagrinidnio grafiko objektas
    """

    # pradiniai kintamieji
    if not tikrinti_df(df, [x]):  # Patikrina, ar df yra pandas.dataFrame su x stulpeliu
        return None
    if not y:  # y nenurodytas
        df_stulpeliai_be_datos = list(set(df.columns) - {x})
        if df_stulpeliai_be_datos:
            y = df_stulpeliai_be_datos[0]  # priskirti pirmąjį stulpelį, kuris nesutapo su x
        else:
            print('Kitų duomenų nei data nėra')
            return None
    elif not tikrinti_df(df, y):  # Patikrina, ar df yra pandas.dataFrame su y stulpeliu
        return None
    df = df.sort_values(by=y)  # dėl visa ko užtikrinti rikiavimą pagal datą

    # paruošti datos vaizdavimą
    format_date1 = mpl_dates.DateFormatter('%Y-%m')  # datos formatas metai-mėnuo
    plt.gca().xaxis.set_major_formatter(format_date1)  # metai-mėnuo datos formatas bus taikokmas x ašiai

    # df[x] turi būti pandas._libs.tslibs.timestamps.Timestamp, antraip busmaklaidos:
    # TypeError: Invalid object type
    # pandas._libs.lib.maybe_convert_numeric; TypeError: Invalid object type at position 0

    if not isinstance(df[x].iloc[0], pd.Timestamp):  # pd.Period ir kt.
        # print(f'Datos kintamojo reikšmės buvo {type(df[x].iloc[0])} tipo, laikinai konvertuosime į pandas.Timestamp')
        df[x] = df[x].apply(lambda t: t.to_timestamp())  # konvertuoti į pandas.Timestamp

    # piešimas
    grafikas = sns.lineplot(data=df, x=x, y=y)  # pats grafikas
    plt.grid(True)  # tinklelis
    plt.xticks(rotation=30)  # teksto, esančio x ašyje, pasukimas
    plt.xlabel('Laikas (metai-mėnuo)')
    if pavadinimas:
        plt.title(pavadinimas)
    plt.tight_layout()  # apkirpti nuo tuščių vietų ir išplėsti matomas paveviksliuko dalis, kad viskas tilptų
    if rodyti:  # ar atvaizduoti kaip galutinai išbaigtą paveiksliuką?
        plt.show()
    return grafikas


def mėnesio_pavadinimas(mėnesių_skaičiai):
    """
    Lietuviškų mėnesių pavadinimai pagal pateiktą mėnesių numerių sąrašą.
    :param mėnesių_skaičiai: sąrašas sveikųjų skaičių nuo 1 iki 12 bet kokia tvarka ir bet kokiu pasikartojimu.
    :return: sąrašas atitinkamų mėnesių pavadinimų
    """

    mėnesių_pavadinimai = [
        'sausis', 'vasaris', 'kovas', 'balandis', 'gegužė', 'birželis',
        'liepa', 'rugpjūtis', 'rugsėjis', 'spalis', 'lapkritis', 'gruodis'
    ]
    if type(mėnesių_skaičiai) in [int, float]:
        return mėnesių_pavadinimai[int(mėnesių_skaičiai) - 1]
    elif type(mėnesių_skaičiai) in [list, pd.DataFrame]:
        return [mėnesių_pavadinimai[int(x) - 1] if ((type(x) in [int, float]) and (x in range(1, 13))) else None
                for x in mėnesių_skaičiai
                ]


def tikrinti_df(df, kintamieji=None):
    """
    Patikrina, ar df yra pandas.DataFrame ir turi nurodytus kintamuosius
    :param df: pandas.DataFrame
    :param kintamieji: tikrintinų stulpelių pavadinimų sąrašas
    :return: True, jei df tinkamas; False, jei netinkamas
    """
    if not isinstance(df, pd.DataFrame):  # jei tai ne pandas.DataFrame
        return False
    if kintamieji is None:
        return True
    elif isinstance(kintamieji, list):
        if all([(m in df.columns) for m in kintamieji]):
            return True
        else:
            trūkstami_stulpeliai = list(set(kintamieji) - set(df.columns))
            print("Tikėtasi, kad df bus pandas.DataFrame su stulpeliais:", trūkstami_stulpeliai)
            return False
    elif isinstance(kintamieji, str) or isinstance(kintamieji, int):
        if kintamieji in df.columns:
            return True
        else:
            print("Tikėtasi, kad df bus pandas.DataFrame bent su stulpeliu:", kintamieji)
            return False
    else:
        print("Tikėtasi, kad parametras kintamieji bus sąrašas arba None")
        return False


def metai_žodžiu(metai):
    """
    Konvertuoja metų skaičius į tekstą
    :param metai: metų skaičiai
    :return: metų sąrašas kaip tekstas
    """
    metai_pd = pd.Series(metai)  # konvertuoti į pandas.Series lentelę
    metai_unik = sorted(metai_pd.unique())  # unikalių metų sąrašas
    metai_str = ', '.join([str(x) for x in metai_unik])  # pats konvertavimas į tekstą, metus skiriant kableliu
    return metai_str


def main():
    """
    Pagrindinė funkcija dviejų elektros duomenų rinkinių – buitinių ir verslo vartotojų – analizės iškvietimui.
    :return:
    """
    print('\n=== Visų elektros duomenų analizė prieš jungiant su kitais duomenimis ===')
    for rinkinio_id in ['buitis', 'verslas']:
        print('\n== %s ==\n' % rinkinio_id.upper())
        # analizuoti visus elektros duomenis per visą laikotarpį, po to tik stabiliausius 2022 m.
        analizuoti_elektros_duomenis(rinkinio_id, metai=2022)

    print('\n=== Jungtinių duomenų analizė, kur imami tik persidengiantys regionai ir laikotarpiai ===')
    ankstesnis_laikotarpis = None
    for rinkinio_id in ['buitis', 'verslas']:
        # analizuoti tik tuos elektros duomenys, kurių regionai bendri su kitų tipų (orų, gyventojų) duomenimis
        # o analizei naudotojas galės pats pasirinkti regionus ir laikotarpius
        ankstesnis_laikotarpis = analizuoti_jungtinius_duomenis(
            el_rinkinio_id=rinkinio_id,
            laikotarpis_orams_ir_gyventojams_nebeanalizuoti=ankstesnis_laikotarpis  # dalies neanalizuos, jei sutaps
        )
    print("\nAnalizė baigta.")


if __name__ == '__main__':
    main()
