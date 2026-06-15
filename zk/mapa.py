import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import random


def generuj_stezky_tukanu(seed=None, nazev_souboru="moje_mapa_tukanu.png"):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    # 1. NASTAVENÍ BAREV A TERÉNU (podle hry)
    tereny = {
        'les': {'color': '#4CAF50', 'label': 'L'},  # Zelená
        'poust': {'color': '#FFF176', 'label': 'P'},  # Žlutá
        'hory': {'color': '#A1887F', 'label': 'H'},  # Hnědá
        'jezero': {'color': '#64B5F6', 'label': 'J'}  # Modrá
    }
    typy_terenu = list(tereny.keys())

    # 2. GEOMETRIE MAPY (Axiální souřadnice pro hexagony)
    velikost_mapy = 5  # Poloměr ostrova
    hex_body = []
    for q in range(-velikost_mapy, velikost_mapy + 1):
        for r in range(max(-velikost_mapy, -q - velikost_mapy), min(velikost_mapy, -q + velikost_mapy) + 1):
            hex_body.append((q, r))

    # Rozdělení na obvod (pro vesnice) a vnitřek (pro hraní)
    obvod = [n for n in hex_body if max(abs(n[0]), abs(n[1]), abs(-n[0] - n[1])) == velikost_mapy]
    vnitrek = [n for n in hex_body if n not in obvod]

    # 3. PŘÍPRAVA VESNIC A PAMÁTEK
    # Ve hře jsou vždy dvojice vesnic A-E (celkem 10)
    vesnice = list("AABBCCDDEE")
    random.shuffle(vesnice)
    pamatky = ["❶", "❷", "❸", "❹", "❺"]  # Symboly památek
    pozice_pamatek = random.sample(vnitrek, k=min(len(pamatky), len(vnitrek)))

    # 4. VYKRESLOVÁNÍ
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')

    def axial_to_pixel(q, r):
        x = 1.5 * q
        y = np.sqrt(3) * (r + q / 2)
        return x, y

    # Vykreslení hracích polí (vnitřek)
    for q, r in vnitrek:
        x, y = axial_to_pixel(q, r)
        teran_key = random.choice(typy_terenu)

        # Vykreslení hexagonu
        hex_patch = patches.RegularPolygon((x, y), numVertices=6, radius=0.95,
                                           orientation=0, facecolor=tereny[teran_key]['color'],
                                           edgecolor='#444444', linewidth=1.5, alpha=0.9)
        ax.add_patch(hex_patch)

        # Přidání památky, pokud tam je
        if (q, r) in pozice_pamatek:
            idx = pozice_pamatek.index((q, r))
            ax.text(x, y, pamatky[idx], ha='center', va='center', fontsize=20, fontweight='bold', color='white')

    # Vykreslení vesnic po obvodu
    # Seřadíme obvodové hexy podle úhlu, aby vesnice byly hezky dokola
    obvod.sort(key=lambda n: np.arctan2(axial_to_pixel(n[0], n[1])[1], axial_to_pixel(n[0], n[1])[0]))

    # Vybereme 10 rovnoměrných pozic na obvodu pro vesnice
    indexy_pro_vesnice = np.linspace(0, len(obvod) - 1, 10, dtype=int)
    for i, idx in enumerate(indexy_pro_vesnice):
        q, r = obvod[idx]
        x, y = axial_to_pixel(q, r)
        # Bílý čtvereček pro vesnici
        ax.text(x, y, vesnice[i], ha='center', va='center', fontsize=22, fontweight='black',
                bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.3'))

    # 5. FINÁLNÍ ÚPRAVY
    plt.xlim(-velikost_mapy * 1.8, velikost_mapy * 1.8)
    plt.ylim(-velikost_mapy * 1.8, velikost_mapy * 1.8)
    ax.set_axis_off()

    seed_label = seed if seed else "Random"
    plt.title(f"OSTROV TUKANŮ\n(Custom Mapa - Seed: {seed_label})", fontsize=20, fontweight='bold', pad=20)

    # Uložení
    plt.savefig(nazev_souboru, dpi=300, bbox_inches='tight')
    print(f"Mapa byla úspěšně uložena jako: {nazev_souboru}")
    plt.show()


# --- SPUŠTĚNÍ ---
# Změň číslo v 'seed', pokud chceš vygenerovat jinou mapu.
# Stejný seed = vždy stejná mapa.
generuj_stezky_tukanu(seed=152)