# Eco-AI

Web app locale : export CSV Cursor → coût exact (prix configurés) → Monte Carlo (énergie × intensité CO₂ ou eau) → CDF et quartiles.

## Lancer

Python 3.11+

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000).

## CSV Cursor

En-têtes exigés (ordre libre, noms exacts) :

`Date`, `Cloud Agent ID`, `Automation ID`, `Kind`, `Model`, `Max Mode`, `Input (w/ Cache Write)`, `Input (w/o Cache Write)`, `Cache Read`, `Output Tokens`, `Total Tokens`, `Cost`

Mapping métier (bug d’export Cursor, figé) :

| Colonne CSV | Sens |
|---|---|
| `Input (w/ Cache Write)` | cache write |
| `Input (w/o Cache Write)` | input |
| `Cache Read` | cache read |
| `Output Tokens` | output |

Colonne `Cost` ignorée. Une colonne manquante, inconnue, ou un champ tokens non entier → erreur, pas d’estimation partielle.

Les modèles CSV sont rattachés au **préfixe configuré le plus long**. Les modèles hors seed (souvent des variantes GPT non listées) apparaissent dans la liste d’omis s’ils pèsent ≥ 1 % des tokens.

## Paramètres

Les jeux de paramètres sont les fichiers `data/settings/*.json`. Au premier lancement, si le répertoire est vide, `defaults/settings.json` est copié vers `data/settings/cursor.json`. Les priors numériques et leurs sources sont dans [`defaults/SOURCES.md`](defaults/SOURCES.md).

## Tests

```bash
pytest
```
