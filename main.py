import analize
import modeliavimas


def main():
    print('\n === Elektros energijos suvartojimo analizės ir prognozavimo sistema === \n')
    analize.main()  # Surinkti ir / arba įkelti duomenis bei atlikti jų analizę
    modeliavimas.main()  # Įkelti arba sukurti modelį ir jį išbandyti


if __name__ == '__main__':
    main()
