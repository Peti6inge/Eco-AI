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
| `gemini-3.1-pro` | input 2e-6, output 12e-6 | Grille Google Gemini 3.1 Pro Preview, contexte ≤ 200k ($2 / $12 / MTok) ; Cursor n’expose pas un tarif propre |
| `gemini-3.8-flash` | input 0.75e-6, output 3.75e-6 | Grille intro Gemini 3.8 Flash jusqu’au 31 déc. 2026 ($0,75 / $3,75 / MTok) ; σ un peu plus large (routing Cursor / tarif standard 2027 $1,50 / $7,50) |
| `gemini-3-flash` | input 0.5e-6, output 3e-6 | Grille Google Gemini 3 Flash ($0,50 / $3 / MTok) |
| `gemini-3-flash-preview` | même tarif que `gemini-3-flash` | Même analogie API ; σ un peu plus large (preview / routing) |
| `claude-4.5-haiku` | input 1e-6, output 5e-6 | Grille Anthropic Claude Haiku 4.5 ($1 / $5 / MTok) |
| `claude-4.5-haiku-thinking` | même tarif que `claude-4.5-haiku` | Thinking facturé comme output côté API ; μ/σ énergie plus larges (tokens de raisonnement inconnus) |
| `claude-opus-4-7-thinking-xhigh` | input 5e-6, output 25e-6 | Grille Anthropic Claude Opus 4.7 ($5 / $25 / MTok) ; σ plus large (effort thinking xhigh, pas de kWh publié) |
| `gpt-5.6-luna-high`, `gpt-5.6-luna-none` | input 0.2e-6, output 1.2e-6 | Grille OpenAI GPT-5.6 Luna ($0,20 / $1,20 / MTok) ; effort Cursor `high` vs `none` : même analogie tarifaire, μ/σ énergie distincts |
| `gpt-5.6-sol-high` | input 4e-6, output 20e-6 | Grille OpenAI GPT-5.6 Sol ($4 / $20 / MTok) |
| `grok-bot-default` | input 5e-6, output 25e-6 | Comme `auto` : bot / routeur Cursor, mélange inconnu |

Cache : **cache_read ≈ 0,1 × input**, **cache_write ≈ 1,25 × input** (convention Anthropic prompt-cache, appliquée à tous les modèles faute de grilles publiques homogènes).

## Intensité énergétique `kWh / $`

Le `$` est un prix API, pas le coût électricité. Un prior large `μ ≈ 0,12 kWh/$` (σ ≈ 0,08) reflète : (i) quelques Wh à quelques dizaines de Wh par requête frontier, (ii) un markup API élevé par rapport à l’énergie. `auto` et `grok-bot-default` ont un σ plus large (routeur). Les variantes thinking / effort `high` élargissent σ ; `luna-none` et Haiku (small) baissent un peu μ.

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
