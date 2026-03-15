class Prvek:
    def __init__(self, id, nazev, poznamka=""):
        self.id = id
        self.nazev = nazev
        self.poznamka = poznamka
        self.is_leaf = False
        self.deti = []  # Pro stanice/budovy

    def pridej(self, prvek):
        self.deti.append(prvek)

class KoncovyPrvek(Prvek):
    def __init__(self, id, nazev, adresa, port, popis, algoritmus, poznamka=""):
        super().__init__(id, nazev, poznamka)
        self.adresa = adresa
        self.port = port
        self.popis = popis
        self.algoritmus = algoritmus
        self.is_leaf = True