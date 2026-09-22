# Suivi TP2 — checklist

> **⚠️ Consigne de référence.** Ce document n'est **pas** un document du prof et ne doit
> **pas** être pris comme référence. C'est uniquement un **calepin de suivi de notre
> avancement** (aide-mémoire). **Toute information ou tâche doit être explicitement
> lue et résolue à partir de `TP2.md`** (et, pour les questions, du document
> `reports/tp2.md` qui en découle). Ne jamais inférer une tâche d'une ligne de ce
> fichier : si ce n'est pas dans `TP2.md`, on ne le fait pas.

Règle : on coche au fur et à mesure, on suit `TP2.md` à la lettre.

## Tâche A — Config GCP + VM

- [x] Projet GCP créé → **phrase** : mets l'ID `tp2-group-u` (pas le nom d'affichage « Tp2-group-u ») partout.
- [x] Billing rattaché au projet → **phrase** : sans billing, `make gcp-bootstrap` échoue (`URQ_PROJECT_BILLING_NOT_FOUND`).
- [x] `make gcp-bootstrap` → **phrase** : active les APIs, crée le repo AR `ml520`, le SA `ml520-vm`, le firewall port 22.
- [x] VM `ml520-vm` créée → **phrase** : `e2-standard-2`, Ubuntu 24.04, 30 GB, zone `northamerica-northeast1-b`.
- [x] `make vm-ssh-config` → **phrase** : l'IP est éphémère, à refaire après chaque `vm-start`.
- [x] `make vm-setup` → **phrase** : installe docker, uv, screen, rsync, make sur la VM.

## Tâche B — Démarrer l'API avec uv

- [x] `uv sync` sur la VM → **phrase** : dans `/opt/inferapi`, crée le venv.
- [x] `.env` écrit à la main → **phrase** : génère le token avec `secrets.token_urlsafe(32)`, colle le **même** sur laptop et VM.
- [x] `make model-train` → **phrase** : entraîne le modèle sur la VM (et sur le laptop) ; le `.joblib` arrive dans `out/models/`.
- [x] **3 `TODO(LAB)` dans `scripts/entrypoint.sh`** → **phrase** : les 3 remplacements sont écrits sur la VM (⚠️ `exec .venv/bin/gunicorn` avec chemin relatif, pas `gunicorn` seul — sinon `command not found`).
- [x] **Test** → **phrase** : `make serve-entrypoint` → healthz = 200 ; `./scripts/sendPayload.sh` = preuve `/v1/predict`.

## Tâche C — systemd

- [ ] **Édite `deploy/inferapi.service`** sur le **laptop** → **phrase** : à la place du `TODO(LAB)` mets `User=mlops`, `WorkingDirectory=/opt/inferapi`, `EnvironmentFile=/opt/inferapi/.env`, `ExecStart=/opt/inferapi/scripts/entrypoint.sh`, `Restart=on-failure`, puis `[Install] WantedBy=multi-user.target`. ⚠️ **Ensuite, sur la VM**, copie-le dans `/etc` avec `sudo cp` **puis édite la copie** : la ligne `ExecStart` doit pointer vers `/opt/inferapi/.venv/bin/gunicorn` (le chemin relatif ne marche pas dans le PATH systemd).
- [ ] **`make vm-sync`** → **phrase** : copie le `.service` édité vers la VM.
- [ ] **Installe le service sur la VM** → **phrase** : `sudo cp /opt/inferapi/deploy/inferapi.service /etc/systemd/system/`, puis `sudo systemctl daemon-reload`, puis `sudo systemctl enable --now inferapi` (pas `restart --now` : après un simple `cp` le service n'est pas installé).
- [ ] **Vérifie** → **phrase** : `systemctl status inferapi` doit dire `active (running)` ; si `inactive`, il ne tourne pas → `journalctl -u inferapi` pour voir l'erreur.
- [ ] **Preuve de survie** → **phrase** : tue le process gunicorn (`ps aux | grep gunicorn` puis `kill`), `systemctl status` doit montrer qu'il **redémarre** → capture.
- [ ] `make vm-forward` → **phrase** : la preuve pour le rapport est cette commande, lancée **avant** ctrl-c ; vérifie avec `curl localhost:8000/healthz` dans un autre terminal.

## Tâche D — runs en parallèle

- [ ] **`screen -S runs` EN PREMIER** → **phrase** : sinon tu devras relancer la VM → nouvelle IP → recopier les fichiers édités.
- [ ] **`make runs-parallel`** → **phrase** : ne l'arrête pas ; attends ~10 min que les 9 runs finissent (les coeurs sont **partagés**, pas 30 Go de RAM : 2 vCPU). Dans screen : Ctrl-a, puis **D**, puis déconnexion.
- [ ] **Preuve écran** → **phrase** : reconnexion → `screen -ls` (le « runs » tourne encore → capture), `cat out/logs/parallel_runs.log` (l'aperçu des 9 runs est **dans ce fichier**).
- [ ] **Fin des 9 runs** → **phrase** : `cat out/runs/*.log` → **attends** qu'ils aient **tous** fini avant la capture.

## Tâche E — image Docker

- [ ] **`.dockerignore` d'abord** → **phrase** : sans lui tu copies tes secrets dans l'image ; ignore au minimum `.env`, `out/`, `data/dataset.csv` (mais **pas** `data/dataset.parquet` ni le modèle — le modèle est copié explicitement à la main).
- [ ] `docker context ls` → **phrase** : doit afficher un context `docker-desktop`.
- [ ] **`PLATFORMS = linux/amd64`** sur le **laptop** → **phrase** : puce Apple ; sinon l'image ne tourne pas sur la VM amd64.
- [ ] **Dockerfile** (`nano Dockerfile`, TODOs à l'intérieur) → **phrase** : copie l'exemple du TP ; **ne copie pas** la ligne `ENV` du prof telle quelle — l'artefact doit être copié explicitement, pas via `COPY .` (qui amènerait `out/` et `.env`).
- [ ] `make docker-build` → **phrase** : `--platform linux/amd64` sur le **laptop** ; copie aussi `scripts/entrypoint.sh` et `configs/` !
- [ ] `make docker-run` → **phrase** : dans un terminal dédié.
- [ ] **Puis sur la VM** → **phrase** : refais l'Étape 1 (`vm_sync.sh`, l'option `--info=progress2` ne marche pas avec openrsync), puis `make docker-build` **aussi** là-bas.
- [ ] `make docker-push` → **phrase** : l'image part vers Artifact Registry (tag `0.2.0`).

## Tâche F — docker compose

- [ ] **`docker-compose.yaml` à la RACINE** → **phrase** : service `inferapi` = image avec **tag** `northamerica-northeast1-docker.pkg.dev/tp2-group-u/ml520/inferapi:0.2.0`, token via **fichier env**, healthcheck **dans le conteneur**, `restart: unless-stopped` ; **ne modifie pas `loadgen`**.
- [ ] `make compose-up` → **phrase** : **d'abord sur le laptop** ; sur la VM ça ne marche pas tant que le yaml n'a pas ses TODOs remplis.
- [ ] **Sur la VM ensuite** → **phrase** : `sudo systemctl stop inferapi.service`, `cd /opt/inferapi`, `make docker-pull`, `make compose-up` sur la VM, puis le `curl` vers `http://<ip-de-la-VM>:8000/v1/predict` (copie la requête **exacte** de TP1) → `jq`, et `docker compose logs loadgen | less` → ces logs ne sont **pas** dans `out/logs/app.log`.

## Rendu

1. **Édite `reports/tp2.md`** (laptop) → **phrase** : réponses aux questions du rapport, d'après `TP2.md` (⚠️ _pas_ un quelconque `GUIDE-ORDRE-EXECUTION.md` — ce fichier n'existe pas dans `TP2.md` ; ne pas inventer de source) + tes captures dans `reports/img/`.
2. **Copie les fichiers édités sur la VM** (Étapes 5→9 : `scripts/entrypoint.sh`, `deploy/inferapi.service`, `docker-compose.yaml`, requête dans `test-requests/`, `.joblib` entraîné **au laptop**) → **phrase** : `vm_sync.sh` ignore `out/`, `scripts/`, `reports/` et `.env` — copie-les **à la main** — puis `git add`/`git commit` tes fichiers à toi. **Jamais** `.env`/token dans le bundle : l'archive `.bundle` contient **tout** l'historique git.
3. `make submit TEAM=<numéro binôme>` → **phrase** : dépose `tp2_starter.bundle` dans Moodle.
4. **Enfin seulement** : `make vm-delete` → **phrase** : ne supprime **pas** le disque persistant 30 GB (à vérifier dans l'interface web), et **éteins** la VM entre les sessions.

## Pièges connus

- **IP éphémère** : chaque `make vm-stop` change l'IP → relance `make vm-ssh-config` ; si tu avais édité `~/.ssh/config` à la main, édite le **script qui le génère**, pas le fichier.
- `uv.lock` copié **avant** le code pour que Docker cache les couches (rien à faire de spécial pour toi).
- Logs du conteneur dans `out/logs/app.log` disparaissent avec le conteneur ; `docker compose logs` persiste — **c'est ça que tu captures**.
- Token **unique** : un par laptop et un par VM, **généré**, jamais tapé.
