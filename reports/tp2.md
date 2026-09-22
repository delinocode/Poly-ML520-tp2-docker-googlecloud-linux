# TP2 - Rapport d'équipe

Équipe : <numéro>
Membres : <noms>

## Question 1 - Deux façons de garder un processus en vie

Les runs ont tourné dans un `screen` et le service tourne sous `systemd`.

Qu'arrive-t-il à `screen` quand la VM redémarre ?

Les runs ont continué à tourner dans screen pendant la coupure SSH, à la reconnexion,j'ai fais `screen -ls` et cela montre toujours `7058.runs (Detached)` et `parallel_runs.log` contient les 9 runs (`exit_code=0` partout).

J'ai fais screen -r 7058 pour reprendre

Qu'arrive-t-il à `systemd` quand la VM redémarre ?

Tant que la machine est éteinte, rien ne tourne (ni screen, ni systemd). Dès que la VM redémarre, systemd est le premier processus lancé, donc il relance automatiquement le service

Dans deploy/inferapi.service nous avons

(Restart=on-failure

[Install]

# This is necessary so that the service starts again after a reboot.

WantedBy=multi-user.target)

Ce qui permet de relancer le service apres un redemarrage

**Preuve** - `screen -ls` après vous être reconnecté en SSH, alors que les runs tournent encore:

![screen](img/screen.png)

## Question 2 - _Docker image and context_

Nommez trois choses que vous avez exclues dans votre .dockerignore et le pourquoi

.env car on ne veut partager notre token API et donc ce risquer a avoir des utilisations non desirer

.venv est trop lourd et de tout maniere il sera generer automatique par uv sync

data/ on charge le model deja entrainer sur les data , pas besoin du dataset

<hr>

Dans le `Dockerfile`, `uv.lock` est copié **avant** `src/`. Expliquez pourquoi.

Chaque COPY crée une couche, et Docker garde ces couches en cache. On copie uv.lock avant src/ parce qu’il change rarement. Ainsi, si je modifie seulement src/, Docker peut réutiliser la couche de uv sync. Si src/ était copié avant, chaque modification du code pourrait obliger Docker à reconstruire les couches suivantes.

## Question 3 - L'artefact et les logs

Le modèle est présentement copié dans l'image, donc l'étiquette de l'image nomme une paire code + poids.

Quel est l'avantage à l'exécution, et à partir de quelle taille d'artefact vous choisiriez plutôt de le télécharger au démarrage ?

L'image inclut le modèle et le code : pas besoin d'internet pour démarrer le conteneur, on connaît toujours les versions utilisées (le tag `0.2.0` représente le modèle et le code).

Notre modèle ne fait que 2,3 Mo, donc le laisser dans l'image est plus simple et reproductible. À partir de quelques centaines de Mo, on l'exclurait de l'image : on monterait le modèle comme volume, ou on le chargerait au démarrage via `joblib.load()`.

<hr>

Le conteneur écrit dans ce qu'il voit être `out/logs/app.log`

Où sont allés ces logs: qu'arrive-t-il du fichier quand le conteneur est supprimé ?

Ces logs restent dans la couche writable du conteneur. Si le conteneur est détruit ou recréé, ils disparaissent : on ne retrouve ces fichiers que si on les place en volume monté.

Qu'est-ce que `docker compose logs` donne à la place en comparaison aux logs écrits dans `out/logs/app.log`.

docker compose logs donne les mêmes messages que out/logs/app.log, à une différence près : les messages écrits dans out/logs/app.log disparaissent à chaque recréation du conteneur (puisque la couche writable est détruite), tandis que Docker conserve la copie de la sortie standard (stdout).

## Question 4 - Compose sur la VM

**Preuve** - votre image dans Artifact Registry, vue depuis la console GCP, avec son étiquette et ses métadonnées:

![artifact-registry](img/artifact_registry.png)

<hr>

`loadgen` joint le service par `http://inferapi:8000`, sans qu'aucun port ne soit publié entre les deux.
Qu'est-ce qui résout ce nom, et pourquoi une adresse IP serait un mauvais choix ici ?

http://inferapi:8000 fonctionne parce que Docker fournit un serveur DNS pour ses réseaux privés. Chaque conteneur devient joignable par le nom de son service. Une adresse IP aurait été un mauvais choix, parce que les IP internes sont éphémères et changent à chaque redémarrage ou recréation du conteneur. Le nom de service, lui, reste toujours le même.
