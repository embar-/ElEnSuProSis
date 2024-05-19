# ElEnSuProSis
##  Elektros energijos suvartojimo prognozavimo sistema

**Tikslas:** Sukurti modelį, kuris prognozuotų elektros energijos suvartojimą įvairiuose Lietuvos regionuose, 
remiantis demografiniais ir meteorologiniais duomenimis.

**Technologijos:** Python, pandas, Matplotlib/Seaborn, scikit-learn


## Struktūra
Projekto rinkmenos sudėtos šiuose kataloguose:

`data/` Duomenys

`img/` Paveikslai

`models/` Modelis

Pagrindiniame kataloge rasite pagrindines Python `*.py` ir kitas bendrąsias rinkmenas. Rinkmenos UTF-8 koduote.


## Duomenys

`duomenys.py` yra pagrindinė, kurioje esančios Rinkinys ir Lentelė klasės skirtos valdyti duomenis kaip objektus.


### Pradiniai surinkti duomenys

* Surinkti istoriniai AB „Energijos skirstymo operatoriaus“ (ESO) duomenys apie **elektros** energijos suvartojimo 
  duomenys, kuriuos galima rasti Lietuvos atvirų duomenų portale <https://data.gov.lt/> pateikstus pamėnesiui CSV ir 
  platinamus pagal [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.lt) licenciją: 
  * Automatizuotų buitinių vartotojų valandiniai duomenys agreguoti pagal regioną <https://data.gov.lt/datasets/1778/>. 
    2022 m. pirminių duomenų kopija padėta `data/elektra_buitis/` kataloge.
  * Automatizuotų verslo vartotojų valandiniai duomenys agreguoti pagal regioną <https://data.gov.lt/datasets/1907/>. 
    2022 m. pirminių duomenų kopija padėta `data/elektra_verslas/` kataloge.

* Naudojant pasirašytą `meteo_lt.py` surinkti **meteorologiniai** duomenys iš <https://archyvas.meteo.lt/>, įskaitant
  oro temperatūrą, juntamąją temperatūrą, vėjo greitį, slėgį jūros lygyje, santykinį oro drėgnį, kritulių kiekį,
  kuriuos teikia Lietuvos hidrometeorologijos tarnyba prie Aplinkos ministerijos (LHMT) ir platina pagal 
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode.lt) licenciją. 
  Iš svetainės ištrauktų 2022 m. pradinių duomenų kopiją rasite kataloge `data/orai/`

* Surinktos Registrų centro svetainėje <https://www.registrucentras.lt/p/853> talpinamos ir demografinius duomenis 
  turinčios statistinės suvestinės lentelės apie gyventojų skaičius pagal amžių skirtingose savivaldybėse. 
    

### Duomenų valymas ir paruošimas

* Naudojant `pandas`:
  * atrinkti labiau dominantys **kintamieji**, 
  * atmestos duomenų eilutės su **praleistomis reikšmėmis**, 
  * pataisytos duomenų **formato klaidos**, 
  * patikrintos laiko juostos ir UTC **laikas** pakeistas į vietinį, 
  * apskaičiuoti **išvestiniai kintamieji** (pvz., elektros energija, kurią per valandą suvartoja statistinis regiono  
    automatizuotas vartotojas, gyventojų pasiskirstymo pagal amžių procentinė dalis savivaldybėse), 
  * **regionų grupavimo suvienodinamas** (pvz., Registrų centre miestų ir rajonų savivaldybės atskirtos, o ESO regionai 
    beveik visas tokias sujungia) bei bendrų regionų atrinkimas, 
  * galiausiai sujungtos skirtingos duomenų rūšys į **bendrą lentelę**. 
* Šie darbai **automatizuoti**, tačiau naudotojas, jei nori, gali **interaktyviai** gali pasirinkti 
  * analizės laikotarpį tarp 2021 ir 2023 m. ir
  * regionus (kelis ar visus) sujungimui į bendrą lentelę.


## Apžvalginė analizė

* **2022 m.** pilniausi, tada automatizuotų elektros abonentų skaičius buvo didžiausias.

![abonentų skaičiaus kitimas laike](./img/Elektros%20abonent%C5%B3%20skai%C4%8Dius%20(buitis).png)

* Netolygus automatizuotų elektros abonentų skaičius: didžiausias Vilniaus, Kauno ir Šiaulių regionuose

![abonentų skaičius regionuose](./img/Elektros%20vartotoj%C5%B3%20skai%C4%8Dius%202022%20m%20(buitis).png)

* Elektros energijos vartojimo kitimas yra gana vienodas paros eigoje nepriklausomai nuo mėnesio, netgi gretimuose 
  mėnesiuose perėjus tarp vasaros ir žiemos laiko (t.y. netgi lyginant vasarį ir balandį, rugsėjį ir lapkritį).
* Ryškus elektros vartojimo sezoniškumas: žiemą didžiausias (~10 kWh/val abonentui), o vasarą mažiausias (~5 kWh/val)
* Gyventojų netolygus pasiskirstymas regionuose pagal amžiaus grupes: santykinai daugiausia senyvo amžiaus žmonių
  gyvena Ignalinoje, o santykinai daugiausia jaunimo yra didžiųjų miestų Vilniaus ir Klaipėdos regionuose.

* Elektros duomenų analizę galite atkartoti įvykdę `analize.py`
* Analizei vizualizuoti sukurtas įrankis `zemelapis.py`, kuris nupiešia Lietuvos kontūrą ir pasirinktus duomenis 
  gali atvaizduoti skirtingų dydžių, spalvų skrituliukais ties atitinkamais regionais.
 
## Modelis 
* Sukurtas **atsitiktinių miškų regresijos** (_RandomForestRegressor_ iš scikit-learn) modelis gali **prognozuoti**, 
  kiek elektros energijos (kWh) suvartotų vidutinis pasirinkto Lietuvos regiono automatizuotas vartotojas.
* Nors tai bendras modelis visiems regionams, bet modelio valdymo metodai automatiškai pasiima ir naudoja regionų 
  koordinatės ir atsižvelgia į jas, o ne į regioną kaip kategoriją.
* Sukurta klasė su metodais modelio kaip objekto valdymui (pvz., apmokyti, vertinti, atlikti hiper-paramtrų paiešką, 
  apmokytą modelį įrašyti į diską ir vėliau nuskaityti pakartotiniam naudojimui).
* Įgyvendinta galimybė naudotojui **interaktyviai** rankiniu būdu pasirinkti regioną, norimas veiksnių reikšmes.
* Modelis pasižymi pakankamu tikslumu: 
  * vidutinė standartinė paklaida (MSE) yra `0,107` naudojant 8 nepriklausomus kintamuosius:    

| Veiksnys                | Svarba   |
|-------------------------|----------|
| Platuma                 | 0,393513 |
| Temperarūra (C)         | 0,195525 |
| Slėgis (hPa)            | 0,113199 |
| Drėgnis (%)             | 0,073408 |
| Vėjo greitis (m/s)      | 0,067726 |
| Valanda                 | 0,067652 |
| Gyventojai 60 m. + (%)  | 0,061465 |
| Ilguma                  | 0,027512 |

Viską galima išbandyti iškviestus `modeliavimas.py`
