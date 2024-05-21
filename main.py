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


import analize
import modeliavimas


def main():
    print('\n === Elektros energijos suvartojimo analizės ir prognozavimo sistema === \n')
    analize.main()  # Surinkti ir / arba įkelti duomenis bei atlikti jų analizę
    modeliavimas.main()  # Įkelti arba sukurti modelį ir jį išbandyti


if __name__ == '__main__':
    main()
