# TP1 - Développement Python pour le ML: structure de projet, bonnes pratiques, qualité de code

## Objectifs

- Mettre en place un projet Python géré par `uv`, en disposition `src/`, avec un fichier `uv.lock` commité.
- Migrer le travail exploratoire d'un notebook hérité vers un paquet structuré, puis reposer le notebook sur ce paquet plutôt que de le laisser en dupliquer le contenu.
- Répartir des dépendances héritées en dépendances de projet, groupes de dépendances et extras, avec des contraintes de versions en intervalles.
- Séparer la configuration (commitée, relue) des secrets (jamais commités, typés `SecretStr`).
- Reconnaître les dépendances passées en paramètres qui rendent le service testable sans modèle ni fichier de configuration.
- Servir le modèle derrière une API FastAPI fournie, et journaliser chaque requête avec le module `logging`.
- Savoir déboguer votre programme, plutôt que de faire des `print()` _statements_.

## Aperçu

Un notebook vous est remis. On ignore qui l'a écrit et il n'y a personne à qui poser la question: il ne reste que les notes laissées en chemin. Muni de vos apprentissages de ML520, vous savez que s'appuyer entièrement sur un notebook ne suffit pas.

Le notebook se trouve dans `./notebooks/` et contient un modèle d'apprentissage automatique et certains essais pour arriver à une solution.

Le notebook contient certaines choses vues en industrie ; certaines pratiques sont acceptables, d'autres moins ; un notebook est généralement pour une exploration ou un rapport.
Vous avez à votre disposition, notamment:

- Le notebook
- Un fichier `requirements.txt` (exporté de `pip freeze -l`)
- Une implémentation d'un modèle pour prédire: **ne vous souciez pas du modèle en soi, le but ici n'est pas de modéliser**.

Les notes laissées dans le notebook sont marquées 📝: elles expliquent _pourquoi_ certaines choses ont été faites. Elles ne disent pas toutes la vérité.

Le travail est donc de transformer ce notebook petit à petit, pour y mettre un peu d'ordre et s'assurer que le projet ne tombera pas à l'eau. Sommairement vous devrez:

1. Remettre de l'ordre dans les dépendances héritées et outiller le projet (qualité de code, débogueur)
1. Faire la migration du code du notebook dans `src`
    - Faire en sorte que le notebook ait les mêmes fonctionnalités en utilisant des `import` de votre code dans `src`
1. Sortir la configuration et les secrets du code
1. Remplacer les `print()` par de la journalisation avec le module `logging`
1. Rendre le tout utilisable en ligne de commande et derrière l'API fournie

## Prérequis

1. Installer `uv` et `git` (Windows: activer WSL2).
1. Cloner le dépôt de départ
1. Récupérer les données de Moodle en CSV et parquet et les placer dans `data/dataset.csv` et `data/dataset.parquet` respectivement
1. Créer votre `.env` local en copiant `.env.example` et mettre une valeur aléatoire (commande dans le fichier `.env.example`).
1. Rouler `make install` pour créer l'environnement virtuel (attention, il est vide!)

## Instructions

Afin que le lab ne soit pas _excessivement_ long, nous vous fournissons du code sous `src/` ainsi que de fichiers de départ.

1. **Implémenter** tous les commentaires marqués **`# TODO(LAB)`**:
    - Respectez les signatures de fonction
1. **Effectuer les tâches** ci-dessous
1. Prenez soin de **répondre aux questions** dans `reports/tp1.md`

**Commencez par la [tâche A](#tâche-a---gestion-des-dépendances).** Tant que les dépendances ne sont pas déclarées, votre environnement virtuel est vide: `make tests`, `make code-quality` et `inferapi ...` échouent tous.


Quelques tests sont déjà fournis: nous nous attarderons dans une semaine ultérieure à leur construction.
Ils sont volontairement peu nombreux et pas très parlant: `make tests` qui passe dire que le code roule - cela ne veut pas dire que le code est validé (au sens large du terme)
Les tests doivent passer à la fin du lab.

Il peut être tentant de passer plus de temps sur le modèle, mais l'exercice ici est d'appliquer les pratiques de _Software Engineering for ML_.

## Commandes

`make help` liste toutes les cibles. Chacune ne fonctionne qu'une fois la tâche correspondante faite.

```bash
make install        # crée .venv à partir de uv.lock
make model-train    # entraîne et écrit out/models/model.joblib
make serve          # gunicorn + workers uvicorn (pour Windows natif: make serve-dev)
make serve-debug    # démarre le service et attend un débogueur sur le port 5678
make tests          # pytest
make code-quality   # ruff (lint + format)
make notebook-launch   # JupyterLab
make submit TEAM=X  # crée le bundle de remise
```

Une fois le service démarré (`/healthz` et `/version` sont ouverts, `/v1/predict` exige le jeton):

```bash
curl localhost:8000/healthz
curl localhost:8000/version
curl -X POST localhost:8000/v1/predict \
  -H "ML520-API-Key: $(make secrets-show)" \
  -H 'Content-Type: application/json' -d '{
  "age": 41, "job": "technician", "marital": "married", "education": "university.degree",
  "default": "no", "housing": "yes", "loan": "no", "contact": "cellular",
  "month": "may", "day_of_week": "thu", "campaign": 1, "pdays": 999, "previous": 0,
  "poutcome": "nonexistent", "emp.var.rate": 1.1, "cons.price.idx": 93.994,
  "cons.conf.idx": -36.4, "euribor3m": 4.857, "nr.employed": 5191.0}'
```

Pour lancer un entraînement:

```bash
uv run inferapi train --output out/models/deep.joblib --max-depth 16 --n-estimators 300
uv run inferapi train --output out/models/eager.joblib --decision-threshold 0.3
uv run inferapi --log-level DEBUG train --output out/models/model.joblib
```

## Tâches

### Tâche A - Gestion des dépendances

But: S'assurer que le projet ait:

- une gestion de dépendances avec uv
- avec le(s) bon(s) groupe(s) de dépendance(s), si applicable
- avec le(s) bon(s) extra(s) de dépendance(s), si applicable
- le tout avec des contraintes en intervalles qui ont une bonne pertinence

Directives / pistes:

- Analyser ce qui est utilisé dans le notebook
- Un groupe `dev` doit exister et être utilisé pour installer toutes les dépendances utiles lorsqu'on roule localement
- La cible `make notebook-launch` s'attend à un groupe nommé `notebooks`
- Tout ce qui est dans `requirements.txt` n'a pas nécessairement sa place ; tout ce qui est nécessaire n'y est pas forcément.
- `scikit-learn-intelex` n'est valide que pour les architectures x86/amd64: vos contraintes doivent le refléter.
- Une fois la migration faite, `requirements.txt` n'a plus de raison d'être: supprimez-le, ou régénérez-en un à partir de votre `pyproject.toml` si vous y tenez (`uv export`)

### Tâche B - Outils de qualité de code
But:

- Avoir du code _linting_ avec `ruff`
- Avoir du code _format_ avec `ruff`
- Faire passer le code en roulant `make code-quality`: vous devez vous assurer que ceci passe partout et ce jusqu'à la fin du lab

Directives / pistes:

- Ne PAS modifier les règles configurées
- Si vous mettez ruff dans les dépendances, assurez vous qu'ils soient dans la bonne section
- Les erreurs `F401` du départ sont les imports que votre implémentation utilisera: implémentez-les plutôt que de les effacer avec `ruff check --fix`
- Assurez-vous qu'à la **fin du lab**, ces tests passent


### Tâche C - Configuration typée
But:

- Compléter `InferApiSettings`: les sections dont le service a besoin
- Compléter `SecurityConfig` (voir [tâche G](#tâche-g---gestion-des-secrets))

Directives / pistes:

- Le reste de `config.py` est fourni, analysez `TrainingSettings`, il est similaire à ce que vous devez faire
- Les valeurs viennent de `configs/config.yaml`
- Variables de `TrainingSettings` et `InferApiSettings` utilisent le préfixe `ML520_` et `__` entre les niveaux
- Les deux objets lisent le même fichier YAML
- Note: L'entraînement n'a pas besoin du jeton de l'API et le serveur n'a pas besoin des hyperparamètres


### Tâche D - Migration du notebook vers `src/`
But:

- Avoir les tâches importantes et réutilisées dans `src`
- Migrer le pipeline et l'entraînement dans `train.py`

Directives / pistes:

- `data.py` est fourni au complet: charger un fichier et appeler `train_test_split` n'est pas ce que ce cours évalue. Lisez-le tout de même, `get_dataset` ne découpe pas comme le notebook
- Ne PAS laisser d'hyperparamètre en dur dans `src/`: ils viennent tous de la configuration
- Garder les signatures fournies
- Garder les deux étapes nommées du pipeline: `data_processor` (le `ColumnTransformer`) et `model`
- Ce qui reste dans le notebook, c'est ce qu'un humain lit: histogrammes, courbes ROC et précision-rappel, tableau de seuils
- Le notebook installe et active `scikit-learn-intelex` en plein milieu (`! pip install`, puis `patch_sklearn()`): ces cellules n'ont pas leur place dans le résultat final. Une dépendance se déclare dans `pyproject.toml` (tâche A et question 1)
- `%load_ext autoreload` puis `%autoreload 2` évitent de redémarrer le noyau à chaque modification sous `src/`
- Note: Vous devriez obtenir à peu près les mêmes performances / même comportement


### Tâche E - Métriques d'évaluation
But:

- Migrer le `evaluate()` vers `get_model_evaluation_metrics()` (dans `train.py`)
- Prendre le seuil dans `training.decision_threshold`
- Évaluer sur l'ensemble de **validation**
- Journaliser les métriques dans un seul événement `model_trained`, depuis `training_procedure()`

Directives / pistes:

- NOTE: Les métriques sont déjà choisies. Vous n'avez pas à les changer, mais vous devez comprendre pourquoi il y en a six et pas une ; laquelle est la plus importante selon vous?
- NOTE: En théorie il faudrait réentraîner sur l'ensemble de notre jeu de données une fois notre modèle choisi. Ceci n'est pas fait dans notre cas.


### Tâche F - Le débogueur
But:

- Savoir déboguer avec un débogueur
- Être capable de faire ces trois choses:
    - arrêter l'exécution sur un point d'arrêt
    - inspecter une variable locale
    - évaluer une expression dans la console de débogage
- Savoir s'attacher à un processus déjà démarré (`make serve-debug`)

Directives / pistes:

- Avant de commencer, lire [le rapport](./reports/tp1.md): certaines étapes doivent être prouvées par capture d'écran
- Les captures d'écran se commitent dans `reports/img/` et se référencent depuis le rapport en markdown
- Les configurations sont fournies dans `.vscode/launch.json` (PyCharm/etc.: créer les équivalentes, `Module`/`inferapi.cli` et `Module`/`uvicorn`)
- Sélectionner `.venv/bin/python` comme interpréteur
- `debugpy` est déjà dans le `requirements.txt`: à vous de choisir son groupe de dépendances
- `make serve-debug` attend que votre éditeur s'attache avant de commencer:
    - Pour atteindre un point d'arrêt dans `create_app()`, l'attente est préconisée, sinon ce serait trop rapide.

### Tâche G - Gestion des secrets
But:

- Ajouter `security.api_token`, typé `SecretStr`
- Faire échouer le chargement de la configuration si la vérification est active sans jeton
- Ajouter la validation de `SecurityConfig`

Directives / pistes:

- Le jeton n'apparaît PAS dans `configs/config.yaml`
- `.env.example` n'est pas lu, il agit en tant que _template_
- Note: Un `SecretStr` se lit avec `.get_secret_value()`
- Le _flag_ `security.enable_api_key_check` doit gérer l'ajout du middleware ou non


### Tâche H - Journalisation avec `logging`
But:

- Remplacer les `print()` du notebook par des appels au module `logging` de la bibliothèque standard dans `src/`
- Avoir un niveau paramétrable par la configuration
- Avoir `out/logs/app.log` (paramétrable par la configuration) qui capture toujours le niveau `DEBUG`
- Écrire la ligne qui clôt chaque requête `/v1/predict`

Directives / pistes:

- Un _Handler_ pour la sortie stdout est fournie dans `logging_setup.py`, vous devez en créer un autre pour le fichier
- Faire attention au niveau du handler à ajouter
- Chaque module demande son logger avec `logging.getLogger(__name__)`: les noms sous `inferapi.` héritent du logger `inferapi`
- La configuration des _logs_ faite une seule fois, dans l'_entrypoint_ du programme, **jamais** dans le _global scope_ d'un module
- Utilisez le _lazy evaluation_: `logger.info("... latency_ms=%s", valeur)`, plutôt qu'une f-string. Le message reste un gabarit stable, et rien n'est formaté si le niveau est désactivé
- L'application est fournie: le seul endroit où il vous manque une ligne est la fin du gestionnaire `/v1/predict`, dans `app.py`
    - Cette ligne doit permettre de répondre à « quelle requête », « quel modèle », « combien de temps » et « qu'a-t-on répondu »
    - `request_id` est sauvegardé dans `request.state`. Le middleware fourni fait ceci: reprend l'en-tête `X-Request-ID` de l'appelant s'il y en a un, et en génère un sinon.
    - Vous pouvez lire `request.state` dans votre route
- En utilisant le `logging`, le format ne peut pas être contrôlé / _parsed_ - ou du moins ce n'est pas garanti. Cependant, si vous utilisez le format:
    - `clé=%s`, il est alors possible de filtrer ou agréger est nommée dans le message
    - Une phrase lisible reste la bienvenue à côté (ex: voir `busy_wait` dans `app.py`)
- On ne journalise pas les données, mais on peut journaliser des ID de requêtes (déjà fait pour vous). Pour les besoins de la cause, on journalise la prédiction en sortie
- Pour le transfert du notebook vers le _repo_: Une ligne de `print()` ne donne pas forcément une ligne de log: les six lignes imprimées après l'évaluation peuvent être combinées en un seul appel à logging
- NOTE: Au démarrage, le service journalise ET affiche avec `print` tous ses réglages en DEBUG: c'est voulu; aussi, vous verrez ce que `SecretStr` fait du secret
- NOTE: Ces lignes restent du texte, il est _possible_ de les _parse_, mais d'autres techniques sont plus adaptées.

### Tâche I - Ligne de commande (CLI)
But:

- Avoir un point d'entrée avec `argparse` dans `cli.py` avec les cibles suivantes:
    - `inferapi data-convert`
    - `inferapi train --output <chemin>` <- à vous d'implémenter avec les directives ci-bas
- Déclarer le point d'entrée du paquet dans `pyproject.toml`

Directives / pistes:

- Implémenter la sous command `inferapi train`
- L'analyseur d'arguments (`argparse`), le _flag_ `--output` et la superposition des _flags_ (`settings_from_args`) sont fournis: le reste des _flags_ (options) est à vous
- Un _flag_ absent vaut `None` et n'affecte PAS l'objet de configuration
- Un _flag_ présent l'emporte sur tout le reste (en terme de priorité)
- L'ordre de priorité n'est pas réécrit dans `cli.py`: les _flags_ sont donnés à `pydantic-settings` comme kwargs d'initialisation (`init_settings`). 
- `config.py` décide du reste (_flags_, environnement, `.env`, YAML, valeurs par défaut)
- Pour ce TP, `--output` et `--overwrite` ne sont pas des _flags_ de configuration (dans le YAML)
    - N.B.: `make model-train` appelle votre CLI avec `--overwrite`

### Tâche J - Le service
But:

- Implémenter `SklearnPredictor` (l'ABC `Predictor` est fournie)
- Faire fonctionner l'application dans `src/inferapi/serve.py`

Directives / pistes:


- Note: L'application est construite par une fonction dans app.py, un patron _Builder_ typique.
- Implémenter `serve.py`
- Implémenter `SklearnPredictor` dans `src/inferapi/predictor.py`
- Pour la version d'un modèle, nous n'avons pas encore défini une façon de versionner nos modèles (un autre cours), mais vous pouvez utiliser la date de création / de modification du fichier pour l'instant.
- Rappelez-vous que `make tests` doit passer

## Questions (à répondre dans `reports/tp1.md`)

**Regarder et répondre aux questions dans `reports/tp1.md`.**

## Critères de remise

- Le rapport est commité dans `reports/tp1.md` avec captures d'écran référencées
- Tout le travail est commité, puis _packaged_ avec `make submit TEAM=<numéro>`, qui produit `out/tp1_team_<numéro>.bundle` via `git bundle`.
    - Si vous ne pouvez pas rouler `make`: `git bundle create "out/tp1_team_REPLACEME.bundle" --all`
- Remettez ce fichier `.bundle` sur Moodle. Notez qu'il contient tout l'historique de commits.
- Vous pouvez vérifiez son contenu en roulant `git clone tp1_team_<numéro>.bundle verification/`.

## Critères d'évaluation

Généralement, il faut que tous les `TODO(LAB)` soient remplis et que l'application soit fonctionnelle. En addition à cela:

- (10 pts) Gestion des dépendances
    - Répartition appropriée des dépendances entre dépendances de projet, groupes et extras.
    - Contraintes de versions exprimées en intervalles: `uv.lock` commité et cohérent avec `pyproject.toml`.
- (5 pts) Outils de qualité de code
    - Le code passe `make code-quality` sans modification des règles originales.
- (10 pts) Configuration typée
    - Configuration typée bien découpée: deux objets de réglages, hyperparamètres compris, aucun hyperparamètre en dur.
- (10 pts) Migration du notebook vers `src/`
    - Le code dans src est complet
    - Bon équilibre entre code laissé dans le notebook et code transféré dans `src/`.
    - Notebook est en bon état: il importe la majorité depuis `inferapi`, ne redéfinit plus rien qui existe dans `src/`, et s'exécute de bout en bout.
- (5 pts) Métriques d'évaluation
    - Métriques migrées, calculées sur la validation, journalisées dans une seule ligne qui contient `model_trained`.
- (5 pts) Le débogueur
    - Preuve d'utilisation du débogueur (à mettre dans le `reports/tp1.md`)
- (5 pts) Gestion des secrets
    - Gestion correcte du secret: `SecretStr`, absent du dépôt et des logs
    - Échec clair et rapide (`fail-fast`) si la vérification est active sans jeton (application FastAPI)
- (10 pts) Journalisation
    - Journalisation conforme: _lazy evaluation_ (en `%s`), niveau paramétrable, valeurs nommées (`request_id`, `model_version`, `latency_ms`) sur `/v1/predict`, DEBUG toujours capturé dans `out/logs/app.log`.
    - Configuration faite une seule fois à l'entrypoint, `getLogger(__name__)` dans chaque module.
    - Utilisation du bon niveau de log.
- (5 pts) Ligne de commande
    - Ligne de commande fonctionnelle, avec la bonne précédence entre les _flags_, les variables d'environnement et la config YAML.
- (10 pts) Le service
    - `SklearnPredictor` et `serve.py` implémentés et fonctionnels
- Critères globaux
    - L'application est fonctionnelle
    - L'entraînement est possible
    - Les tests passent
    - Il ne reste pas de TODO
- (0 à -20 pts) Critères de remise
    - Une remise qui ne respecte pas les [critères de remise](#critères-de-remise) s'expose à une pénalité négative
- (25 pts)  Réponse aux questions:
    - Réponses claires et argumentées aux questions du rapport.
    - 5 pts par question
    - 5 pts pour l'extrait de logs
