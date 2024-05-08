import os.path
import pandas as pd
from matplotlib import pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
import seaborn as sns
import joblib  # modelio įrašymui ir įkėlimui
import zemelapis  # regiono koordinatėms pridėti


def sukurti_modelį(n_estimators=100, random_state=0, **papildomi_modelio_parametrai_kuriant):
    """
    Sukurti atsitiktinių miškų regresoriaus (RandomForestRegressor) modelį
    :param n_estimators: medžių/balsuotojų skaičius
    :param random_state: (ne)atsitiktinė būsena rezultatų atkartojimui
    :param papildomi_modelio_parametrai_kuriant: kiti parametrai
    :return: RandomForestRegressor modelis
    """
    modelis = RandomForestRegressor(  # atsitiktinių miškų regresorius
        n_estimators=n_estimators,  # medžių/balsuotojų skaičius
        random_state=random_state,  # (ne)atsitiktinė būsena rezultatų atkartojimui
        **papildomi_modelio_parametrai_kuriant  # kiti parametrai
    )
    return modelis


class RFR1Modelis:
    """
    Klasė el.suvartojimo modeliui valdyti
    """

    def __init__(self, tyliai=False,
                 vardas_saugojimui='RFR_modelis_elektrai', katalogas_saugojimui='models',
                 **papildomi_modelio_parametrai_kuriant
                 ):
        self.X_mok = None  # įvesties  duomenys apmokymui
        self.X_tst = None  # įvesties  duomenys testavimui
        self.y_mok = None  # apmokymo  duomenų  rezultatas
        self.y_tst = None  # testavimo duomenų  rezultatas
        self.priklausomo_kintamojo_vardas = None  # pakeičimas per .sukurti_modelį()
        self.nepriklausomi_kintamieji = None  # pakeičimas per .sukurti_modelį()
        self.regionai_apmokyme = None
        self.metai_apmokyme = None
        self.modelis = sukurti_modelį(**papildomi_modelio_parametrai_kuriant)
        self.apmokytas = False
        self.mse = None
        self.svarbiausi_veiksniai = None
        self.vardas_saugojimui = vardas_saugojimui
        self.katalogas_saugojimui = katalogas_saugojimui
        if not tyliai:
            print('RFR modelis inicijuotas. Dabar galite apmokyti su .apmokyti()')

    def __str__(self):
        """
        Grąžina labai trumpą aprašymą vietoj techninio identifikatoriaus
        """
        return 'RandomForestRegressor modelis ' + ('jau apmokytas' if self.apmokytas else 'dar neapmokytas')

    def info(self):
        """
        Atspausdina informaciją apie modelį
        """
        print('Modelis gali prognozuoti, kiek elektros energijos (kWh) suvartotų '
              'vidutinis pasirinkto Lietuvos regiono automatizuotas vartotojas.')
        print('Nors tai bendras modelis visiems regionams, bet modelio valdymo metodai automatiškai '
              'pasiima ir naudoja regionų koordinatės.')
        print(self)
        if self.apmokytas:
            print(' pagal metus:', self.metai_apmokyme)
            print(' su regionais:\n  ', ', '.join(self.regionai_apmokyme))
            print('\nModelio vertinimas:')
            if self.mse:
                print(f' vid. st. paklaida: {self.mse:.4f}')
            print(' veiksniai pagal svarbumą:')
            print(self.svarbiausi_veiksniai)

    def paduoti_duomenis_apmokymui(
            self, df, priklausomo_kintamojo_vardas=None, nepriklausomi_kintamieji=None, tyliai=False
    ):
        """
        Tik įkelia duomenis, bet modelio apmokymo nepradeda.
        :param df: pandas.DataFrame lentelė arba kelias iki CSV.
        :param priklausomo_kintamojo_vardas: priklausomo kintamojo vardas pandas.DataFrame lentelėje
        :param nepriklausomi_kintamieji: nepriklausomų kintamųjų vardai pandas.DataFrame lentelėje
        :param tyliai: ar slėpti kai kuriuos išsamesnius paaiškinimus
        """

        """ Pradiniai kintamieji """
        if isinstance(df, str) and os.path.isfile(df) and df.endswith('.csv'):
            try:
                df = pd.read_csv(df)
            except Exception as err:
                print('Nurodyta rinkmena netiko importuoti su pandas.read_csv():', err)
                return
        if not isinstance(df, pd.DataFrame):
            print('Apmokymui priimami tik pandas.DataFrame() tipo duomenys. Tam žr. duomenys.py')
            return

        """ Priklausomo kintamojo vardas, vėliau y """
        y_numatytieji_vardai = [
            'Vid. reg. ab. suvartojimas (kWh/val)',
            'Vid. reg. ab. suvartojimas (st.)',
            'Suvartojimas (kWh/val)',
            'Suvartojimas (st.)', ]
        if isinstance(priklausomo_kintamojo_vardas, str) and (priklausomo_kintamojo_vardas in df.columns):
            pass  # viskas gerai su naudotojo paduotu
        if isinstance(self.priklausomo_kintamojo_vardas, str) and (self.priklausomo_kintamojo_vardas in df.columns):
            priklausomo_kintamojo_vardas = self.priklausomo_kintamojo_vardas  # imti išsaugotą objekto savybėse
        else:  # ieškoti tarp numatytųjų vardų
            priklausomo_kintamojo_vardas = None
            for x_vardas in y_numatytieji_vardai:
                if x_vardas in df.columns:
                    priklausomo_kintamojo_vardas = x_vardas
                    break
            if not priklausomo_kintamojo_vardas:
                print('Nėra ką toliau daryti, nes pandas.DataFrame duomenys nei vieno iš šių kintamųjų:\n ',
                      '\n '.join(y_numatytieji_vardai))
                return

        """ Nepriklausomų kintamųjų vardai, vėliau naudojami kuriant X """
        # papildomai pridėti regiono koordinates, jei jų nėra, bet regionas yra
        if ('Regionas' in df.columns) and (('Platuma' not in df.columns) or ('Ilguma' not in df.columns)):
            platuma, ilguma, regionai_be_koordinačių = zemelapis.gauti_koordinates_regionams(df['Regionas'])
            if not regionai_be_koordinačių:  # jei nėra regionų be koordinačių, t.y. jas turi visi regionai
                df['Platuma'], df['Ilguma'] = platuma, ilguma  # įtraukti į df
        skaitiniai_kintamieji = {
            st for st in df.columns if (df[st].dtype.name in ['int32', 'int64', 'float64'])  # jei  skaičiaus tipas
        }
        standartizuoti_kintamieji = {k for k in list(df.columns) if isinstance(k, str) and k.endswith(' (st.)')}
        neprasmingi_kintamieji = {
            priklausomo_kintamojo_vardas, *y_numatytieji_vardai,  # būtina išmesti patį priklausomąjį kintamąjį!
            'Abonentai', 'Metai', 'Laikotarpis',  # pastovūs kintamieji, vietoj laikotarpio turim mėnesį
            'Gyventojai', 'Gyventojai 0–6 m.', 'Gyventojai 7–17 m.', 'Gyventojai 18-59 m.', 'Gyventojai 60 m. +'
        }
        nereikalingi_laiko_kintamieji = {'Mėnuo'}  # nes per daug padeda modeliui # 'Sav_diena', 'Sav. diena', 'Valanda'
        # Nepriklausomi kintamieji = visi skaičitiniai, išskyrus neprasmingus ir standartizuotus
        # (Random Forests sėkmingai veikia ir su nestandartizuotais kintamasiais, tad pastarųjų nereikia)
        if isinstance(nepriklausomi_kintamieji, list):  # tikrinti naudotojo prašomus
            nepriklausomi_kintamieji = [
                k for k in nepriklausomi_kintamieji if (isinstance(k, str) and k in list(df.columns))]
            if not nepriklausomi_kintamieji:
                print('Prašomi nepriklausomi kintamieji nerasti')
                return
        else:  # automatiškai parenkami
            nepriklausomi_kintamieji = list(
                skaitiniai_kintamieji - neprasmingi_kintamieji -
                standartizuoti_kintamieji - nereikalingi_laiko_kintamieji
            )

        if not nepriklausomi_kintamieji:  # matyt per daug išmetėme kintamųjų...
            if skaitiniai_kintamieji - neprasmingi_kintamieji:  # jei bent jau turėjome standatizuotus
                nepriklausomi_kintamieji = list(skaitiniai_kintamieji - neprasmingi_kintamieji)
                if not tyliai:
                    print('Naudojami visi skaitiniai, išskyrus neprasmingi kintamieji')
            else:
                print('Neradome tinkamų priklausomų kintamųjų')
                return

        print('Modeliui apmokyti naudojami kintamieji:\n   '
              'Priklausomas:  ', priklausomo_kintamojo_vardas, '\n   '
                                                               'Nepriklausommi:', ', '.join(nepriklausomi_kintamieji))
        # įsiminti priklausomą ir neprilkausomus kintamuosius kaip objekto savybes
        self.priklausomo_kintamojo_vardas = priklausomo_kintamojo_vardas
        self.nepriklausomi_kintamieji = nepriklausomi_kintamieji

        X = df[self.nepriklausomi_kintamieji]
        y = df[self.priklausomo_kintamojo_vardas].values

        # Padalinimas į mokymo ir testavimo duomenis
        self.X_mok, self.X_tst, self.y_mok, self.y_tst = train_test_split(
            X, y, train_size=0.5, test_size=0.25, random_state=0
        )
        # Regionai
        if 'Regionas' in df.columns:
            self.regionai_apmokyme = sorted(df['Regionas'].unique())  # įsimenami unikalūs regionai
        if 'Metai' in df.columns:
            self.metai_apmokyme = sorted(df['Metai'].unique())  # įsimenamas laikotarpis

        # Nunulinti vertinimus:
        self.svarbiausi_veiksniai = None
        self.mse = None

    def apmokyti(self, df=None, tyliai=False, **papildomi_modelio_parametrai_apmokant):
        """
        Apmokyti modelį
        :param df: None - imti anksčiau paduotus duomenis; galite pateikti savo pandas.DataFrame lentelę arba CSV kelią
        :param tyliai: ar slėpti kai kuriuos išsamesnius paaiškinimus
        :param papildomi_modelio_parametrai_apmokant: papildomi parametrai perduodami į RandomForestRegressor().fit()
        """

        if df is not None:
            self.paduoti_duomenis_apmokymui(df, tyliai=tyliai)
        elif (self.X_mok is None) or (self.y_mok is None):
            print('Nėra nurodytų ar anksčiau įkeltų duomenų apmokymui')
            return

        # Pats apmokymas
        if not tyliai:
            print('Modelis apmokomas...')
        self.modelis.fit(self.X_mok, self.y_mok, **papildomi_modelio_parametrai_apmokant)
        self.apmokytas = True
        if not tyliai:
            print('Modelis sėkmingai apmokytas. Dabar galite .prognozuoti() ir .vertinti()')

    def prognozuoti(self, x_tst=None):
        """
        Prognozuoti elektros energijos suvartojimą.
        :param x_tst: numatytuoju atveju ima iš metaduomenų (None), bet naudotoojas gali pats nurodyti vienos eilutės
        dydžio pandas.DataFrame kaip nepriklausomus kintamuosius įvesčiai į jau apmokytą modelį prognozavimui
        :return: prognozuojama(-os reikšmės) elektros suvartojimo reikšmės pagal apmokytą atsitiktinių miškų modelį
        """
        if not self.apmokytas:
            print('Modelis dar neapmokytas. Apmokykite su .apmokyti()')
            return

        if x_tst is None:  # jei naudotojas nepateikė priklausomų kintamųjų
            if (self.X_tst is not None) and len(self.X_tst):  # jei neturim
                return self.modelis.predict(self.X_tst)
            else:
                print('Nėra vidinių testavimo duomenų ir nepateikėte duomenų prognozavimui.')
        else:
            try:
                return self.modelis.predict(x_tst)
            except Exception as err:
                print('Modelio panaudojimo prognozavimui klaida:', err)

    def vertinti(self, tyliai=False, su_grafiku=True):
        """
        Apskaičiuojama vidutinė standartinė paklaida (MSE) ir veiksnių svarbumas.
        :param tyliai: ar slėpti kai kuriuos išsamesnius paaiškinimus
        :param su_grafiku: ar nubraižyti sveiksnių svarbumo grafiką
        """
        if not self.apmokytas:
            print('Modelis dar neapmokytas. Apmokykite su .apmokyti()')
            return

        if not tyliai:
            print('\nModelio įvertinimas:')
        if (self.y_tst is not None) and len(self.y_tst):  # jei netuščias y_tst
            if self.X_tst is not None:  # jei netuščias y_tst
                RFR_spėjimas = self.prognozuoti()  # apmokyto modelio spėjimas su naujais duomenimis
                self.mse = mean_squared_error(self.y_tst, RFR_spėjimas)
                if not tyliai:
                    print(f'Vidutinė standartinė paklaida: {self.mse: .4f}')
            else:
                print('Netikėtai .y_tst ir .X_tst reikšmės yra tuščios. Negalime apskaičiuoti modelio paklaidos.')

        self.svarbiausi_veiksniai = pd.DataFrame(
            self.modelis.feature_importances_, index=self.nepriklausomi_kintamieji,
            columns=['Svarba']).sort_values('Svarba', ascending=False)
        if not tyliai:
            print(self.svarbiausi_veiksniai)
            print()

        if su_grafiku:
            plt.figure(figsize=(14, 6))
            sns.barplot(x=self.svarbiausi_veiksniai.Svarba, y=self.svarbiausi_veiksniai.index)
            plt.title('Svarbiausi veiksniai prognozuojant elektros suvartojimą kWh/val. regiono abonentui pagal RFR' +
                      (f'\n(Vidutinė st. paklaida = {self.mse:.4f})' if self.mse else '')
                      )
            plt.xlabel('Veisknių svarbos lygis')
            plt.ylabel('Veiksniai')
            plt.tight_layout()
            plt.show()

    def saugoti(self, vardas_saugojimui=None):
        """
        Įrašyti modelį į diską pakartotiniam naudojimui vėliau su joblib ir jo metaduomenis į .txt
        :param vardas_saugojimui: rinkmenos vardas be galūnės, nes pastarosios pridėsimos automatiškai
        :return: [True|False] ar pavyko išsaugoti
        """
        if self.apmokytas:
            if not vardas_saugojimui:
                vardas_saugojimui = self.vardas_saugojimui

            if isinstance(vardas_saugojimui, str) and vardas_saugojimui:
                if isinstance(self.katalogas_saugojimui, str) and self.katalogas_saugojimui:
                    nepilnas_kelias = os.path.join(self.katalogas_saugojimui, vardas_saugojimui)
                else:
                    nepilnas_kelias = self.vardas_saugojimui
                joblib_kelias = nepilnas_kelias + '.joblib'

                try:
                    joblib.dump(self.modelis, joblib_kelias, compress=3)  # įrašyti
                    self.vardas_saugojimui = vardas_saugojimui  # atnaujinti metaduomenis
                    print('Modelis sėkmingai įrašytas į', joblib_kelias)
                except Exception as err:
                    print('Nepavyko įrašyti modelio į %s: %s' % (joblib_kelias, err))

                # Papildomi metaduomenys:
                if self.svarbiausi_veiksniai is None:  # veiksniai pagal svarbumą, jei nėra
                    self.vertinti(tyliai=True, su_grafiku=False)  # svarbiausios savybės
                if self.svarbiausi_veiksniai is not None:  # jei yra veiksniai (nors gal nebuvo prieš 2 eilutes)
                    df_veiksniai = self.svarbiausi_veiksniai.copy()
                    df_veiksniai = df_veiksniai.reset_index()
                    df_veiksniai.columns = ['Veiksnys', 'Svarba']
                    self.svarbiausi_veiksniai.to_csv(nepilnas_kelias + '.savybes.txt', index=True, sep='\t')
                df_info = pd.DataFrame({  # pagrindinia meta duomenys
                    'Metai': [self.metai_apmokyme],
                    'Regionai': [self.regionai_apmokyme],
                    'Priklausomas_kintamasis': self.priklausomo_kintamojo_vardas,
                    'Nepriklausomi_kintamieji': [self.nepriklausomi_kintamieji],
                    'MSE': self.mse,
                    'Svarbiausi_veiksniai': [
                        list(self.svarbiausi_veiksniai.index) if (self.svarbiausi_veiksniai is not None) else []
                    ]
                }).transpose().reset_index()
                df_info.columns = ['Informacija', 'Reikšmė']
                df_info.to_csv(nepilnas_kelias + '.info.txt', index=False, sep='\t')
                print('Metaduomenys įrašyti.')

                return True

            else:
                print('Nurodykite rinkmeną saugojimui su joblib')
        else:
            print('Modelis neapmokytas. Kokia prasmė jį saugoti?')
        return False

    def įkelti(self, vardas=None):
        """
        Nuskaito anksčiau įrašytą modelį su joblib ir su jo metaduomenimis
        :param vardas: rinkmenos vardas be galūnės, nes pastarosios pridėsimos automatiškai
        :return: [True|False] ar pavyko įkelti
        """
        if not vardas:
            vardas = self.vardas_saugojimui
        if isinstance(vardas, str) and vardas:
            if (isinstance(self.katalogas_saugojimui, str) and
                    os.path.isfile(os.path.join(self.katalogas_saugojimui, vardas + '.joblib'))):
                nepilnas_kelias = os.path.join(self.katalogas_saugojimui, vardas)
                joblib_kelias = nepilnas_kelias + '.joblib'
            elif os.path.isfile(self.vardas_saugojimui + '.joblib'):
                nepilnas_kelias = self.vardas_saugojimui
                joblib_kelias = nepilnas_kelias + '.joblib'
            else:
                print('Nepavyko rasti .joblib rinkmenos su modeliu')
                return False

            try:
                print(f'Nuskaitomas modelis iš „{joblib_kelias}“...')
                self.modelis = joblib.load(joblib_kelias)  # įkelti
                self.vardas_saugojimui = vardas  # atnaujinti metaduomenis
                print('Modelis įkeltas iš', joblib_kelias)
                self.apmokytas = True
            except Exception as err:
                print('Nepavyko nuskaityti modelio is %s: %s' % (joblib_kelias, err))
            else:

                # bandyti įkelti metaduomenis
                try:
                    df_info = pd.read_csv(nepilnas_kelias + '.info.txt', sep='\t', index_col='Informacija').transpose()
                    # pirma nuskaityti visus meta duomenis jų nepriskririant prie objekto savybių
                    metai_apmokyme = atkoduoti_tekstus(df_info['Metai'])
                    regionai_apmokyme = atkoduoti_tekstus(df_info['Regionai'])
                    priklausomo_kintamojo_vardas = atkoduoti_tekstus(df_info['Priklausomas_kintamasis'])
                    nepriklausomi_kintamieji = atkoduoti_tekstus(df_info['Nepriklausomi_kintamieji'])
                    mse = atkoduoti_tekstus(df_info['MSE'])
                    df_veiksniai = pd.read_csv(nepilnas_kelias + '.savybes.txt', sep='\t', index_col=0)

                except Exception as err:
                    print('Bet meta duomenų įkelti nepavyko:', err)
                    print('Gali neatitikti modelio parametrai, negalėsite naudoti interaktyviam prognozavimui.')
                else:
                    # tik jei pavyko įkelti visus meta duomenis duomenis, juos sudėti į self.
                    self.metai_apmokyme = metai_apmokyme
                    self.regionai_apmokyme = regionai_apmokyme
                    self.priklausomo_kintamojo_vardas = priklausomo_kintamojo_vardas
                    self.nepriklausomi_kintamieji = nepriklausomi_kintamieji
                    self.mse = float(mse)
                    self.svarbiausi_veiksniai = df_veiksniai
                    print('Modelio meta duomenys irgi įkelti sėkmingai.')
                    return True

        else:
            print('Nurodykite rinkmeną nuskaitymui su joblib')
        return False

    def prognozuoti_interaktyviai(self, su_info=True):
        """
        Naudotojoas gali pats interaktyviai suvesti duomenis pavienes veiksnių reikšmes ir
        prognozuoti, kiek elektros energijos (kWh) suvartotų
        vidutinis pasirinkto Lietuvos regiono automatizuotas vartotojas
        :param su_info: ar pradžioje parašyti išsamiai apie modelį
        """
        if not self.apmokytas:
            print('Modelis neapmokytas')

        print('\n= Interaktyvus prognozavimas =\n')
        if su_info:
            self.info()
            print()

        while True:
            regionas = input('Įrašykite regioną, kuriame elektros suvartojimą; '
                             'arba įveskite B, jei norite baigti: \n> ')
            if regionas in self.regionai_apmokyme:
                break
            elif regionas.upper() == 'B':
                return
            else:
                print('Tokio %s regiono nežinome.' % regionas)
        platuma, ilguma, _ = zemelapis.gauti_koordinates_regionams([regionas])
        df_priklausomi_kintamieji = pd.DataFrame()
        for kint in self.nepriklausomi_kintamieji:
            if kint == 'Ilguma':
                df_priklausomi_kintamieji[kint] = ilguma
            elif kint == 'Platuma':
                df_priklausomi_kintamieji[kint] = platuma
            else:
                while True:
                    try:
                        df_priklausomi_kintamieji[kint] = float(input(f'{kint}: >'))
                        break
                    except ValueError:
                        print('Tikėtasi skaičiaus.')
        rezultatas = self.prognozuoti(df_priklausomi_kintamieji)
        print('Vidutinio %s regiono abonento el. energijos prognozuojamas suvartojimas nurodytomis aplinkybėmis:\n'
              ' %.4f kWh/val.' % (regionas, rezultatas[0]))

    def optimizavimas(self):
        """
        Optimalių parametrų paieška
        :return:
        """
        # papildomi importai, jei norima ieškoti optimalesnių modelio parametrų
        from sklearn.model_selection import RandomizedSearchCV
        from scipy.stats import randint as sp_randint

        # Hiperparametrai
        parametrai = {
            'n_estimators': sp_randint(5, 100),
        }

        paieška = RandomizedSearchCV(
            estimator=sukurti_modelį(),
            param_distributions=parametrai,
            n_iter=5,
            n_jobs=-1,
            cv=3,
            random_state=0,
            verbose=1,
        )
        paieška.fit(self.X_mok, self.y_mok)
        print("Geriausias rezultatas %.3f naudojant %s" % (paieška.best_score_, paieška.best_params_))


def atkoduoti_tekstus(tekstas):
    if isinstance(tekstas, pd.Series):
        if len(tekstas) == 1:
            return atkoduoti_tekstus(tekstas.iloc[0])
        else:
            return [t for t in atkoduoti_tekstus(tekstas.iloc[0])]
    if isinstance(tekstas, str) and len(tekstas):
        if tekstas.startswith('[') and tekstas.endswith(']'):
            nariai_txt = tekstas[1:-1].replace("'", "").replace('"', '').split(',')  # atskirti ,
            return [i.strip() for i in nariai_txt]  # bandyti auto-konvertuoti teksto narius
    return tekstas


def main():
    """
    Naudojimo pavyzdys
    """
    modobj = RFR1Modelis(tyliai=True)
    įkeltas = modobj.įkelti()  # bandyti įkelti, jei sukurtas anksčiau
    if not įkeltas:  # nepavykus įkelti
        csv_rinkmena = os.path.join('data', 'apjungtieji_2022.csv')  # apsibrėžti duomenų vietą
        if not os.path.isfile(csv_rinkmena):  # ar yra duomenys?
            import duomenys
            df = duomenys.gauti_visus_sutvarkytus_duomenis()  # Galima išsaugoti:  df.to_csv(csv_rinkmena, index=False)
            if df is None:
                return  # nėra ką daryti be duomenų;
        else:
            df = pd.read_csv(csv_rinkmena)  # nuskaityti duomenis, jei yra

        modobj.paduoti_duomenis_apmokymui(
            df,
            nepriklausomi_kintamieji=[  # jų nurodyti nebūtina - gali parinkti automatiškai
                'Platuma', 'Ilguma',
                'Valanda',
                'Vėjo greitis (m/s)',
                'Temperarūra (C)',
                'Slėgis (hPa)',
                'Drėgnis (%)',
                'Gyventojai 60 m. + (%)'
            ]
        )
        modobj.apmokyti()
        modobj.prognozuoti()  # galima praleisti, nes .vertinti() iškvies, jei trūks
        modobj.vertinti(tyliai=True)  # mse ir svarbiausi veiksniai
        modobj.saugoti()  # įrašyti pakartotiniam naudojimui
    modobj.prognozuoti_interaktyviai()


if __name__ == '__main__':
    main()
