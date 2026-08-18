# Mode d'emploi

Ce guide couvre l'usage courant, une fois l'outil déployé (installation et déploiement : voir `README.md`). Il répond à des questions du type « comment j'ajoute une page à surveiller » ou « où je vais lire les changements détectés », pas à la mise en place technique.

## Ajouter une page à surveiller

1. Créer un fichier de règles dans `rules/`, sur le modèle de `rules/exemple_rules.csv` :

   ```
   Name;MaPage
   PathOut;docs/feeds/MaPage
   Freq;1234567
   Url;https://le-site-a-surveiller.fr/la-page
   DateDebut;2026-08-17
   DateFin;2026-12-31
   MaxItems;50
   ```

   - `Name` : un nom court, sans espace ni accent (il sert de nom de fichier).
   - `PathOut` : toujours sous `docs/feeds/` pour que GitHub Pages le serve.
   - `Freq` : les jours actifs de la semaine, `1`=lundi à `7`=dimanche collés (`1234567` = tous les jours).
   - `Url` : la page à surveiller. Répéter la ligne `Url;...` pour regrouper plusieurs pages dans le même flux RSS.
   - `DateDebut`/`DateFin` : bornes de la fenêtre de surveillance. En dehors, la veille est ignorée (pas d'erreur, juste rien ne se passe).
   - `MaxItems` : nombre de changements gardés dans le flux RSS (l'historique complet, lui, n'est jamais purgé).

2. Ajouter une ligne dans `InputRules_Master.txt` pour que cette veille soit exécutée :

   ```
   Exec;rules/exemple_rules.csv
   Exec;rules/MaPage.csv
   ```

3. Committer et pousser. La veille démarre au prochain passage du cron (voir README pour l'horaire configuré), ou immédiatement via un déclenchement manuel (étape suivante).

## Déclencher une vérification immédiate

Sans attendre le prochain passage du cron : dépôt GitHub → onglet **Actions** → workflow **Veille page web** → bouton **Run workflow**.

## Lire les changements détectés

Le flux RSS d'une veille nommée `MaPage` est accessible à :

```
https://<utilisateur>.github.io/<dépôt>/feeds/MaPage/MaPage.xml
```

À ajouter dans un lecteur RSS (Feedly, NetNewsWire, etc.). Chaque changement détecté apparaît comme un item, avec la date de détection et un résumé du diff (ce qui a été ajouté/retiré, ligne par ligne, façon `git diff` — les lignes commençant par `+` sont ajoutées, celles commençant par `-` sont retirées).

Sans lecteur RSS, le fichier `docs/feeds/MaPage/MaPage.xml` reste lisible tel quel dans un navigateur, ou en ouvrant `docs/feeds/MaPage/MaPage_history.json` (l'historique complet, jamais tronqué).

## Vérifier que la veille tourne bien

Dépôt GitHub → onglet **Actions** → historique des exécutions du workflow. Un run vert = tout s'est bien passé (même si aucun changement n'a été détecté ce jour-là, c'est normal). Un run rouge = une erreur — ouvrir le run pour voir le journal, cause la plus fréquente : page devenue inaccessible (timeout, statut HTTP d'erreur).

## Suspendre ou arrêter une page

- **Suspendre temporairement** : commenter la ligne `Exec;rules/MaPage.csv` dans `InputRules_Master.txt` en la faisant précéder de `#`.
- **Arrêter définitivement** : retirer la ligne `Exec` et, si besoin, supprimer le fichier de règles et le dossier `docs/feeds/MaPage/` correspondant.

## Dépannage courant

- **Le workflow échoue avec une erreur HTTP** : la page a peut-être bougé (redirection, changement d'URL) ou bloque les requêtes automatisées — vérifier l'URL manuellement dans un navigateur.
- **Une page surveillée ne remonte jamais de changement alors qu'elle a visiblement changé** : elle construit peut-être son contenu en JavaScript après chargement (voir « Limites connues » du `README.md`) — le HTML brut récupéré ne contient alors pas le contenu affiché.
- **Le flux RSS ne se met pas à jour** : vérifier dans l'historique des runs Actions que le job s'exécute bien aux dates attendues (jours `Freq`, fenêtre `DateDebut`/`DateFin`), et que le commit automatique du bot a bien poussé (`git log` sur le dépôt de déploiement).
- **Un changement signalé n'est pas pertinent** (variation de publicité, de date affichée, etc.) : c'est une limite connue, voir la section « Limites connues » du `README.md` — le diff est calculé sur tout le contenu Markdown extrait, sans filtrage sémantique.
