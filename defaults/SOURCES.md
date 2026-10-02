# Priors numériques du seed V1

Les valeurs de `defaults/settings.json` sont des **priors d’ordre de grandeur**, pas des mesures Cursor. Les σ sont volontairement larges.

## Prix $/token

Sources publiques (tarif API « list », convertis en $ par token = $ / 1 000 000) :

| Modèle (id) | Approximation | Source / analogie |
|---|---|---|
| `claude-opus-5`, `claude-4.6-opus` | input 15e-6, output 75e-6 | Grille Anthropic Claude Opus (input / output / MTok) |
| `claude-4.6-sonnet` | input 3e-6, output 15e-6 | Grille Anthropic Claude Sonnet |
| `cursor-grok-4.6`, `grok-4.7` | input 3e-6, output 15e-6 | Ordre de grandeur xAI / Cursor (non officiel) |
| `composer-2.5` | input 1.25e-6, output 10e-6 | Prior « modèle interne » Cursor, plus bas qu’un frontier |
| `composer-2.5-fast` | input 0.4e-6, output 1.6e-6 | Prior « small / fast » |
| `auto` | input 5e-6, output 25e-6 | Routeur : mélange, donc plus cher et plus incertain |

Cache : **cache_read ≈ 0,1 × input**, **cache_write ≈ 1,25 × input** (convention Anthropic prompt-cache, appliquée à tous les modèles faute de grilles publiques homogènes).

## Intensité énergétique `kWh / $`

Le `$` est un prix API, pas le coût électricité. Un prior large `μ ≈ 0,12 kWh/$` (σ ≈ 0,08) reflète : (i) quelques Wh à quelques dizaines de Wh par requête frontier, (ii) un markup API élevé par rapport à l’énergie. `auto` a un σ plus large (routeur).

## CO₂ électricité `kg / kWh`

Mix réseau + PPA hyperscale, large :

- OpenAI / Microsoft : ~0,30 kg/kWh (σ 0,15) — mix US + achats d’énergie
- Anthropic / AWS : ~0,35 kg/kWh (σ 0,18)
- Google : ~0,15 kg/kWh (σ 0,10) — mix déclaré plus bas, incertitude conservée
- SpaceXAI : ~0,38 kg/kWh (σ 0,20) — pas de reporting public, prior US moyen

Références d’ordre de grandeur : eGRID US ~0,35–0,40 kg CO₂e/kWh (hors PPA) ; rapports environnementaux hyperscale 2023–2025.

## Eau AWARE `L / kWh`

WUE datacenter + évaporation thermique, pas le volume « consommé » au robinet :

- μ ≈ 1,5–2,2 L/kWh, σ ≈ 1,0 L/kWh (AWARE / WUE publiés ~0,2–1,8 L/kWh selon campus, plus l’amont réseau)

Ce n’est **pas** une ACV ISO ; c’est un prior pour la V1 Monte Carlo.
