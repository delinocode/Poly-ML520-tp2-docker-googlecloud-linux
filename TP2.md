# TP2 - Machines virtuelles, scripting et conteneurisation

## Objectifs

- Provisionner une machine virtuelle sur GCP et la joindre en `ssh`.
- Copier un projet vers un serveur
- Écrire des scripts bash
- Déployer un service ML sur une VM avec `systemd`.
- Lancer des travaux longs (ex: pendant la nuit) sans interruption.
- Construire une image docker et la déployer sur une VM.
- Utiliser docker compose pour orchestrer deux conteneurs.

## Aperçu

Le TP1 vous a donné du code qui roule sur votre machine.
Le TP2 le fait rouler ailleurs de deux façons:

1. En roulant sur la VM avec systemd
2. En roulant un conteneur sur la VM

D'abord sur une VM que vous provisionnez vous-même: vous y copiez ce qu'il faut, vous le démarrez avec un script d'entrée et vous laissez systemd faire l'orchestration.
C'est ainsi qu'on déployait avant les conteneurs (et aussi d'autres services non conteneurisés)

Puis on roule avec des _containers_: vous construisez l'image une fois sur votre portable + vous la poussez dans un _registry_: Artifact Registry.
La VM _pull_ cette image.

## Prérequis

1. Créer un compte GCP avec l'essai gratuit (utilisez votre adresse `@polymtl.ca` pour 300$ USD credits). **Ne cliquez jamais sur « Activer le compte complet »**: l'essai ne facture rien, mais un compte complet oui.
1. Installer `gcloud` et Docker, puis `gcloud auth login`.
1. Nommer votre projet une fois pour votre shell: `export GCP_PROJECT=<votre-projet>`.
   Les cibles `make` refusent de rouler sans cette variable, et aucune d'elles ne devine
   le projet à votre place.
1. Rouler `./scripts/gcp_bootstrap.sh "$GCP_PROJECT"`. Une fois devrait suffire; vous
   devriez avoir de l'information en sortie après quelques dizaines de secondes avec le
   nom du projet, etc.

## Instructions

Cinq fichiers sont à compléter, chacun avec ses commentaires `# TODO(LAB)`:

| Fichier                   | Tâche                                    |
| ------------------------- | ---------------------------------------- |
| `scripts/entrypoint.sh`   | [B](#tâche-b---le-script-de-démarrage)   |
| `deploy/inferapi.service` | [C](#tâche-c---le-service-systemd)       |
| `Dockerfile`              | [E](#tâche-e---limage)                   |
| `.dockerignore`           | [E](#tâche-e---limage)                   |
| `docker-compose.yaml`     | [F](#tâche-f---docker-compose-sur-la-vm) |

Le reste du TP consiste à faire tourner tout ça et à répondre aux questions dans
[`reports/tp2.md`](./reports/tp2.md).
Lisez-les avant de commencer: certaines preuves se prennent en passant et se reproduisent mal après coup.

`make help` liste les cibles. Les nouvelles:

```bash
make gcp-bootstrap
make vm-create
make vm-ssh-config
make vm-setup
make vm-sync
make vm-ssh
make vm-forward
make vm-stop
make vm-start
make vm-delete
make runs-parallel
make serve-entrypoint
make docker-context
make docker-build
make docker-run
make docker-push
make compose-up
make compose-logs
```

## Tâches

### Tâche A - Mettre votre VM en place

1. Créer la VM avec `make vm-create` (ou manuellement si vous êtes brave).
   - N.B.: l'adresse IP est **éphémère** et changera probablement à chaque
     arrêt/démarrage.
   - N.B.: La VM est démarrée lorsqu'elle est créée
1. Configurer SSH avec `make vm-ssh-config`. Ceci fait:
   - la création de l'utilisateur `mlops` sur la VM;
   - une entrée dans votre `~/.ssh/config`.
1. Ouvrez `~/.ssh/config` et lisez l'entrée.
   - Notez que vous pouvez maintenant utiliser `ssh`, `scp`, `rsync` et l'extension
     `Remote-SSH`.
   - Étant donné que l'adresse IP est éphémère, `make vm-start` va réécrire l'entrée de SSH config.
1. Rouler `make vm-setup`, qui va:
   - installer docker, uv, rsync, screen et make;
   - créer `/opt/inferapi` et mettre les bonnes permissions dessus.
1. Rouler `make vm-sync`, qui copie le projet dans `/opt/inferapi`.
   - Lisez `scripts/vm_sync.sh`. Ce qui voyage y est décidé ligne par ligne, et
     `rsync` ne lit pas votre `.gitignore`.
1. Sur la VM, dans `/opt/inferapi`: `uv sync`, écrivez le `.env` à la main, puis
   `make model-train`.
1. Regardez où vous êtes: `nproc`, `free -h`, `df -h`, `ps aux`.
1. `make vm-stop` dès que vous arrêtez de travailler.

Site web de GCP: [https://console.cloud.google.com/](https://console.cloud.google.com/)

**ATTENTION POUR LA REMISE: Ce que vous modifiez sur la VM doit revenir sur votre portable pour être commité!**
`rsync` marche dans les deux sens. (Vous pouvez aussi faire copier+coller)

### Tâche B - Le script de démarrage

Complétez `scripts/entrypoint.sh`. Critères:

- Le script refuse de démarrer sans `ML520_SECURITY__API_TOKEN`
- Le script refuse de démarrer sans artefact de modèle
- Le script démarre gunicorn avec `exec` (`make serve` montre les options à reprendre).

Testez avec `make serve-entrypoint`.

### Tâche C - Le service systemd

But: Avoir l'API de inferapi qui roule avec `systemd`.

Complétez `deploy/inferapi.service`.
Le service doit:

1. rouler comme `mlops`
1. rouler depuis `/opt/inferapi`
1. démarrer par `scripts/entrypoint.sh`
1. lire le jeton de façon sécuritaire (ex: environnement)
1. redémarrer sur échec
1. être démarré au boot.

Sur la VM:

```bash
# Une seule fois
sudo cp deploy/inferapi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now inferapi
curl "http://localhost:8000/healthz"
```

Attendez-vous à vous tromper. Après chaque correction, il faut dire à systemd de recharger les configuations:

```bash
sudo systemctl daemon-reload
sudo systemctl restart inferapi
journalctl -u inferapi
```

Puis tuez le processus avec `kill` et regardez ce qui arrive.

Remarquez qu'en utilisant l'adresse IP publique, vous ne pouvez tout de même pas accéder à la page: `http://<IP>:8000`
Cependant on peut utiliser les tunnels SSH pour ceci:
Depuis votre portable: `make vm-forward`, puis `http://localhost:8000/healthz`.

Le pare-feu n'ouvre pas le port 8000 en entrée; le trafic passe dans le tunnel SSH (donc le port 22, qui lui est ouvert).

### Tâche D - Lancer des travaux et y revenir après déconnexion

`scripts/parallel_runs.sh` est fourni. Lisez-le: il roule chaque combinaison, donne son propre fichier de log à chaque run, écrit un sommaire dans `out/logs/parallel_runs.log`.

N.B.: ceci est didactique. Une vraie recherche d'hyperparamètres utilise Optuna, Ray Tune ou autre.

Sur la VM:

```bash
screen -S runs
make runs-parallel
# Ctrl-A d pour détacher
exit                  # fermez la session SSH
```

Reconnectez-vous, puis `screen -ls` et `screen -r runs`.

Les fichiers produits servent aux questions du rapport.

<!--


  DOCKER


 -->

### Tâche E - L'image

**NOTE: CETTE TÂCHE DOIT ÊTRE FAITE LOCALEMENT, car vous devez bâtir l'image et la pousser dans Artifact Registry depuis votre ordinateur local.**

Complétez `Dockerfile` et `.dockerignore`. L'image doit:

- installer les dépendances depuis `uv.lock`, sans les dépendances de développement;
- ordonner ses instructions pour que le cache serve;
- contenir le modèle, et rien de secret.

N.B.: les motifs du `.dockerignore` ne sont pas _exactement_ ceux d'un `.gitignore`.

```bash
make docker-context   # après avoir écrit le .dockerignore
make docker-build
make docker-run
curl localhost:8000/healthz
```

### Tâche F - Docker compose sur la VM

Complétez le service `inferapi` dans `docker-compose.yaml`.
Le service `loadgen` est fourni et vous ne devez pas le modifier: votre inferapi service devrait fonctionner.

À noter: si vous voulez mettre le service persistent, nous vous conseillons de mettre l'option `restart: unless-stopped`.

Sur votre portable:

```bash
# Construire les conteneurs SUR VOTRE MACHINE
make compose-up
# Pousser les conteneurs sur Artifact Registry
make docker-push
```

Ouvrez ensuite Artifact Registry dans la console GCP et prenez une capture de votre image, avec son étiquette et son empreinte visibles (voir la question dans le rapport)

Sur la VM, dans `/opt/inferapi`:

```bash
# Arrêter le service systemd s'il existe
sudo systemctl stop inferapi
# S'assurer que vous êtes dans le bon dossier
cd /opt/inferapi
# Et que votre fichier est à jour
docker compose config
docker compose pull
docker compose up -d --no-build
docker compose logs inferapi
```

Vérifiez un `/v1/predict` authentifié, puis regardez `docker compose logs loadgen`.

## Critères de remise

- Le rapport est commité dans `reports/tp2.md`, avec les captures dans `reports/img/`.
- Tout le travail est commité, puis empaqueté avec `make submit TEAM=<numéro>`, qui
  produit `out/tp2_team_<numéro>.bundle`.
  - Sans `make`: `git bundle create "out/tp2_team_REPLACEME.bundle" --all`
  - **NE PAS OUBLIE DE RAPATRIER LES FICHIERS DE VOTRE VM DANS VOTRE DOSSIER LOCAL: ex: le `inferapi.service` après avoir fait toutes les modifications.**
- Remettez le `.bundle` sur Moodle. Il contient tout l'historique.
- **Détruisez la VM (et les disques)** avec `make vm-delete` (ou depuis l'interface web)
  une fois le TP remis. Gardez le projet!

## Critères d'évaluation

- (15 pts) Le script de démarrage
  - Les deux vérifications présentes et fonctionnelles
  - gunicorn démarré avec `exec` et les bonnes options
- (15 pts) Le service systemd
  - L'unité est bien écrite
  - L'unité démarre le service par `entrypoint.sh`, lit le jeton depuis un fichier d'environnement et redémarre quand il meurt.
- (20 pts) L'image docker
  - Le Dockerfile est bien écrit:
    - Dépendances installées depuis le fichier de verrouillage, sans les dépendances de développement.
    - Les instructions sont ordonnées pour que le cache serve, et l'image contient le modèle.
- (10 pts) Le contexte de build
  - `.dockerignore` qui exclut le dépôt git, l'environnement virtuel, le dataset et surtout le `.env`.
- (20 pts) Compose, et l'image sur la VM
  - Le service `inferapi` porte le nom de l'image poussée, avec une étiquette de version, et la VM tire cette image-là.
  - Le jeton arrive par l'environnement, et le `healthcheck` teste depuis l'intérieur du conteneur.
  - La capture de la console Artifact Registry est au rapport.
- Critères globaux
  - `make tests` et `make code-quality` passent toujours.
  - Il ne reste pas de `TODO(LAB)`.
- (0 à -20 pts) Critères de remise
  - Une remise qui ne respecte pas les [critères de remise](#critères-de-remise) s'expose à une pénalité négative.
- (20 pts) Réponses aux questions
  - Réponses claires et argumentées, captures d'écran lisibles.
