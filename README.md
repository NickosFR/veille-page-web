# Veille page web — surveillance de pages et flux RSS des changements

Surveille une ou plusieurs pages web entre une date de début et une date de fin,
détecte les changements de contenu à chaque exécution planifiée, et maintient un flux
RSS des changements détectés. Conçue pour tourner sur un cron GitHub Actions,
indépendamment de l'ordinateur personnel.

## Principe

- La récupération de page s'appuie sur une requête HTTP simple (`requests`) suivie
  d'une conversion HTML → Markdown (`markdownify`) — voir `watcher.py`. Pas de rendu
  JavaScript (choix assumé, 2026-08-18, en remplacement de Firecrawl : voir
  `CLAUDE.md`).
- New/same/changed n'est plus un statut renvoyé par un fournisseur externe : c'est
  `pipeline.py` qui compare le markdown récupéré à celui du run précédent (stocké dans
  `<nom>_state.json`, ou dans un Google Sheet si `SheetId` est utilisé — voir plus
  bas). Seule la page introuvable (HTTP 404) est détectée directement dans
  `watcher.py` (`PageRemovedError`).
- Le texte de diff affiché dans le flux RSS est calculé en local avec `difflib`,
  entre le markdown de ce run et celui du run précédent.
- Chaque changement détecté est ajouté à un historique append-only
  (`<nom>_history.json`, ou l'onglet `history` du Sheet) — c'est cet historique daté
  qui permet de répondre au besoin de fenêtre « entre deux dates » : seule la
  comparaison contre le dernier run est possible autrement, jamais entre deux dates
  arbitraires.
- Le flux `<nom>.xml` est régénéré à chaque exécution à partir de cet historique
  (tronqué aux `MaxItems` changements les plus récents).

## Installation locale (pour tester avant déploiement)

```
pip install -r requirements.txt
python main.py InputRules_Master.txt
```

Voir `rules/exemple_rules.csv` et `InputRules_Master.txt` pour un exemple complet et
exécutable.

## Format des fichiers de règles

Une commande par ligne, `Commande;arg1;arg2;...`. `#` démarre un commentaire (en
début de ligne ou après une espace/tabulation). Vide et commentaires ignorés.

**Fichier maître** (`InputRules_Master.txt`) :

| Commande | Effet |
|---|---|
| `Exec;chemin` | Exécute la veille définie dans ce fichier de règles |
| `Stop` | Arrête la lecture du fichier maître |

**Fichier de veille** (un par page ou groupe de pages, dans `rules/`) :

| Commande | Effet |
|---|---|
| `Name;<nom>` | Nom de la veille (fichiers de sortie : `<nom>.xml`, `<nom>_state.json`, `<nom>_history.json`) |
| `PathOut;<dossier>` | Dossier de sortie (créé si absent) ; utiliser `docs/feeds/<nom>` pour être servi par GitHub Pages |
| `Freq;<jours>` | Chiffres collés, 1=lundi...7=dimanche (`135` = lun/mer/ven) ; veille ignorée en dehors de ces jours |
| `Url;<url>` | URL à surveiller (répéter la commande pour surveiller plusieurs pages dans le même flux) |
| `DateDebut;<AAAA-MM-JJ>` | Avant cette date, la veille est ignorée |
| `DateFin;<AAAA-MM-JJ>` | Après cette date, la veille est ignorée |
| `MaxItems;<n>` | Nombre maximum d'items conservés dans le flux RSS (défaut 50) ; l'historique, lui, garde tout |
| `SheetId;<id>` | Optionnel. Bascule l'état et l'historique de cette veille dans le Google Sheet `<id>` (onglets `state`/`history`, créés automatiquement) au lieu des fichiers JSON locaux |
| `Stop` | Arrête la lecture de ce fichier de règles |

### Stockage de l'état et de l'historique : local (défaut) ou Google Sheet

Par défaut, l'état par URL et l'historique des changements vivent dans
`<nom>_state.json`/`<nom>_history.json` (voir `snapshot_store.py`), sauvegardés une seule
fois en fin de run — ce qui suppose que le run va jusqu'au bout.

Avec `SheetId;<id>` (voir `sheets_store.py`), chaque URL traitée écrit immédiatement sa
ligne dans le Sheet, au fil de la boucle — pas de sauvegarde groupée en fin de run. Si le
quota Firecrawl s'épuise en cours de run ou que le job s'arrête prématurément, les URLs
déjà traitées avant l'incident restent acquises : contrairement aux fichiers JSON locaux,
qui ne survivent que si le workflow atteint son étape finale de commit git.

Prérequis (même pattern que `projets/veille-emploi/`, non encore réalisé) :
1. Créer un compte de service Google Cloud, activer l'API Sheets.
2. Partager le Google Sheet cible en accès Éditeur avec l'adresse email du compte de
   service.
3. Poser le JSON du compte de service dans le secret de dépôt
   `VEILLE_PAGE_WEB_GOOGLE_CREDENTIALS` (voir `.github/workflows/veille-page.yml`).

Le flux RSS (`<nom>.xml`) reste, lui, toujours un fichier local publié via GitHub Pages —
seuls l'état et l'historique changent de support.

## Déploiement sur GitHub Actions

1. **Dépôt** : ce dossier doit être un dépôt git avec un remote GitHub (dépôt privé
   recommandé si les pages surveillées ou leur contenu sont personnels ; public si
   le flux RSS doit être accessible sans authentification via GitHub Pages).
2. **Secret du dépôt** (Settings → Secrets and variables → Actions → New repository
   secret) : `VEILLE_PAGE_WEB_GOOGLE_CREDENTIALS`, seulement si au moins une veille
   utilise `SheetId` (JSON du compte de service sur une seule ligne). Sans `SheetId`
   nulle part, aucun secret n'est nécessaire.
3. **GitHub Pages** : Settings → Pages → Source = "Deploy from a branch", branche par
   défaut, dossier `/docs`. Le flux d'une veille nommée `Exemple` avec
   `PathOut;docs/feeds/Exemple` sera alors servi à
   `https://<utilisateur>.github.io/<dépôt>/feeds/Exemple/Exemple.xml`.
4. **Cron** : `.github/workflows/veille-page.yml` déclenche `python main.py
   InputRules_Master.txt` toutes les heures. Ajuster l'expression cron selon le
   besoin réel. Déclenchement manuel possible depuis l'onglet Actions
   (`workflow_dispatch`).
5. **Persistance** : le runner GitHub est jeté à la fin de chaque exécution. Le
   workflow committe et pousse automatiquement `docs/` (flux `.xml`, `*_state.json`
   et `*_history.json` pour les veilles sans `SheetId`) — sans ce commit, chaque run
   repartirait de zéro.

## Secrets

Aucun secret en dur dans le code, aucun requis pour le fonctionnement de base (requête
HTTP simple, sans clé d'API). Seul `VEILLE_PAGE_WEB_GOOGLE_CREDENTIALS` est nécessaire,
et seulement si une veille utilise `SheetId`.

## Limites connues

- **Pas de rendu JavaScript** : une page dont le contenu est construit côté navigateur
  après chargement (fetch différé, hydratation lourde) n'est pas capturée — seul le
  HTML renvoyé tel quel par le serveur est lu. Choix assumé (2026-08-18, en
  remplacement de Firecrawl) pour rester léger sur le runner GitHub Actions, sans
  dépendance externe payante. À vérifier au cas par cas ; une page en rendu serveur
  (SSR/SSG, y compris beaucoup d'apps Next.js) passe généralement sans problème.
- La granularité de détection dépend entièrement de la fréquence du cron : un
  changement suivi d'un retour à l'état initial entre deux vérifications passe
  inaperçu.
- Le diff affiché est un diff texte brut (`difflib.unified_diff`) sur le Markdown
  converti depuis le HTML récupéré, pas un diff HTML structurel — du bruit de mise en
  forme (espacement, ordre d'éléments non significatif) peut apparaître comme un
  changement.
