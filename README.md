# backend-ci : API DentaRDV

Backend de **DentaRDV**, une application de prise de rendez-vous pour une clinique dentaire au Sénégal.
Projet d'examen DevOps, Master 2 SI/SR, UADB, 2026-2027.

Ce dépôt contient uniquement le **backend** (l'API). Le projet suit une architecture **multi-repo** :

| Dépôt | Rôle |
|---|---|
| `backend-ci` (ce dépôt) | API, tests, Dockerfile, Jenkinsfile de CI |
| `frontend-ci` | Interface web (HTML/CSS/JS servi par Nginx) |
| `deployment-cd` | `docker-compose.yml`, `.env`, Jenkinsfile de déploiement |

---

## 1. Le besoin

Une clinique dentaire prend aujourd'hui ses rendez-vous par téléphone, WhatsApp ou sur place. Conséquences : files d'attente, doubles réservations, créneaux oubliés, rendez-vous non honorés.

L'API permet :

- au **patient** (sans compte) de consulter les dentistes, voir les créneaux libres, réserver, suivre et annuler son rendez-vous ;
- au **dentiste** (avec compte) de gérer son planning et de recevoir des notifications ;
- à l'**administrateur** de créer les comptes des dentistes.

---

## 2. Technologies

| Outil | Rôle |
|---|---|
| **Python 3.10+** | Langage |
| **FastAPI** | Construction de l'API et documentation automatique (`/docs`) |
| **Uvicorn** | Serveur qui fait tourner FastAPI |
| **SQLAlchemy** | Accès à la base de données depuis Python |
| **SQLite** | Base locale pour développer et tester (un seul fichier) |
| **PostgreSQL** | Base de données en production (Docker Compose) |
| **bcrypt** | Hachage des mots de passe |
| **PyJWT** | Jetons de connexion (à venir) |
| **pytest** | Tests unitaires |
| **bandit, pip-audit** | Scans de sécurité du code et des dépendances |

---

## 3. Structure du dépôt

```
backend-ci/
├── app/
│   ├── main.py          # Démarrage de l'application, CORS, /health
│   ├── config.py        # Lecture des variables d'environnement
│   ├── database.py      # Connexion à la base (SQLAlchemy)
│   ├── models.py        # Tables : dentiste, soin, rendez_vous, ...
│   ├── schemas.py       # Forme des réponses de l'API
│   ├── services.py      # Règles métier (horaires, créneaux libres, ...)
│   ├── security.py      # Hachage et vérification des mots de passe
│   ├── seed.py          # Données de départ (soins, admin, dentistes de démo)
│   └── routers/
│       ├── public.py        # Routes publiques (dentistes, soins, créneaux)
│       └── rendez_vous.py   # Réservation d'un rendez-vous
├── tests/               # Tests unitaires (pytest)
├── requirements.txt     # Dépendances Python
├── .env.example         # Modèle des variables d'environnement
├── .gitignore
└── README.md
```

---

## 4. Installation et lancement en local

### Prérequis

- Python 3.10 ou plus (`python --version`)
- Git

### Étape 1 : Récupérer le code

```bash
git clone https://github.com/Pm-GUENE/backend-ci.git
cd backend-ci
```

### Étape 2 : Créer l'environnement virtuel

Un environnement virtuel isole les bibliothèques du projet du reste de la machine.

```bash
python -m venv venv
```

Activation :

| Système | Commande |
|---|---|
| Windows (PowerShell) | `venv\Scripts\Activate.ps1` |
| Windows (cmd) | `venv\Scripts\activate` |
| Mac / Linux | `source venv/bin/activate` |

`(venv)` doit apparaître au début de la ligne de commande.

Si PowerShell bloque l'activation, lancer d'abord :
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### Étape 3 : Installer les dépendances

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Étape 4 : Lancer le serveur

```bash
python -m uvicorn app.main:app --reload
```

Au démarrage, l'application :

1. crée la base `dentardv.db` (SQLite) si elle n'existe pas ;
2. crée les tables ;
3. insère les 6 motifs de consultation, le compte administrateur et 3 dentistes de démonstration.

Ces opérations sont **idempotentes** : relancer le serveur ne crée pas de doublons.

### Étape 5 : Vérifier

| Adresse | Résultat attendu |
|---|---|
| http://localhost:8000/health | `{"status":"ok"}` |
| http://localhost:8000/docs | Documentation Swagger interactive |

Arrêter le serveur : `Ctrl + C`.

---

## 5. Configuration (variables d'environnement)

Aucun secret n'est stocké dans le code ni dans Git. Les réglages sont lus dans l'environnement.

| Variable | Rôle | Valeur par défaut (développement) |
|---|---|---|
| `DATABASE_URL` | Adresse de la base de données | `sqlite:///./dentardv.db` |
| `JWT_SECRET` | Clé de signature des jetons | `dev-secret-a-changer` |
| `ADMIN_IDENTIFIANT` | Identifiant de l'administrateur créé au démarrage | `admin` |
| `ADMIN_PASSWORD` | Mot de passe initial de l'administrateur | `admin-dev` |
| `DEMO_PASSWORD` | Mot de passe des dentistes de démonstration | `Demo-dev-2026` |
| `CORS_ORIGINS` | Origines autorisées à appeler l'API | `*` |

`.env.example` donne le modèle avec de fausses valeurs. En déploiement, les vraies valeurs sont fournies par le fichier `.env` du dépôt `deployment-cd` et ne doivent **jamais** être poussées sur GitHub.

Exemple avec PostgreSQL :

```
DATABASE_URL=postgresql+psycopg2://dentardv:mot_de_passe@db:5432/dentardv
```

---

## 6. Modèle de données

```
dentiste (id, nom, specialite, identifiant, mot_de_passe_hash, doit_changer_mdp)
administrateur (id, identifiant, mot_de_passe_hash)
soin (id, libelle)                         # un soin = un motif de consultation
dentiste_soin (dentiste_id, soin_id)       # motifs proposés par chaque dentiste
rendez_vous (id, patient_nom, patient_tel, dentiste_id, soin_id,
             date, heure, statut, cree_le)
```

Points importants :

- **Statuts** : `en_attente`, `confirme`, `termine`, `annule` (sans accent en base ; le frontend affiche les accents).
- **Anti double réservation** : un index unique partiel `uq_creneau_actif` sur `(dentiste_id, date, heure)` pour les rendez-vous `en_attente` ou `confirme`. Même si deux patients réservent au même instant, la base refuse le second.
- Les mots de passe sont stockés **hachés** (bcrypt), jamais en clair.

---

## 7. Règles métier

- Ouvert du **lundi au vendredi**, de **08h00 à 17h00**, créneaux de **30 minutes** (dernier créneau à 16h30).
- Pas de rendez-vous le week-end ni dans le passé.
- Un dentiste ne peut pas avoir deux rendez-vous actifs sur le même créneau.
- Un rendez-vous n'est accepté que si le dentiste propose le motif choisi.
- Statuts : `en_attente` → `confirme` → `termine`. Un rendez-vous `en_attente` ou `confirme` peut passer à `annule`. Un rendez-vous `annule` ou `termine` ne change plus.
- Les règles sont dans `app/services.py`, sous forme de fonctions qui reçoivent l'heure actuelle (`now`) en paramètre, ce qui les rend faciles à tester.

---

## 8. Endpoints

La documentation complète et testable est sur `/docs`. Les dates sont au format `AAAA-MM-JJ`.

### Disponibles

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | État du service |
| GET | `/dentistes` | Liste des dentistes avec leurs motifs. Filtres : `?q=` (nom ou motif), `?soin_id=` |
| GET | `/soins` | Liste des motifs. Filtre : `?dentiste_id=` |
| GET | `/dentistes/{id}/soins` | Motifs proposés par un dentiste (404 si inconnu) |
| GET | `/creneaux?dentiste_id=&du=&au=` | Créneaux libres d'un dentiste sur une période (31 jours maximum) |
| GET | `/rendez-vous/{id}?tel=` | Suivre un rendez-vous (numéro + téléphone). 404 « Rendez-vous introuvable » si le couple ne correspond pas. Renvoie aussi `annulable` |
| PATCH | `/rendez-vous/{id}/annulation?tel=` | Annulation par le patient. 409 si le rendez-vous est terminé, déjà annulé ou passé |
| POST | `/rendez-vous` | Réserver un rendez-vous. Renvoie 201 et le numéro de rendez-vous (`id`). Erreurs : 404 (dentiste ou motif inconnu), 409 (créneau pris), 422 (données ou créneau invalides) |

### À venir

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/connexion` | Connexion dentiste ou administrateur (jeton JWT) |
| PATCH | `/mot-de-passe` | Changement de mot de passe |
| GET | `/admin/dentistes` | Liste des dentistes (administrateur) |
| POST | `/admin/dentistes` | Création d'un dentiste (administrateur) |
| GET | `/mes-rendez-vous` | Rendez-vous du dentiste connecté |
| GET | `/mes-notifications` | Nouveaux rendez-vous et rappels à 15 minutes |
| PATCH | `/rendez-vous/{id}` | Changer le statut (dentiste concerné) |

---

## 9. Tester l'API à la main

Dans `/docs`, cliquer sur une route, puis **Try it out**, remplir les champs et **Execute**. Une route fonctionne quand le **code de réponse** et le **contenu** correspondent à ce qui est attendu.

| Code | Sens |
|---|---|
| 200 | Succès |
| 201 | Ressource créée |
| 404 | Élément introuvable |
| 409 | Conflit (ex. créneau déjà pris) |
| 422 | Données invalides |
| 500 | Erreur du serveur : consulter le terminal |

Vérifications utiles :

| Test | Résultat attendu |
|---|---|
| `GET /dentistes` | 3 dentistes de démonstration avec leurs motifs |
| `GET /dentistes?q=carie` | 2 dentistes |
| `GET /dentistes/99/soins` | 404 |
| `GET /creneaux?dentiste_id=1&du=2026-11-10&au=2026-11-14` | 72 créneaux, de 08:00 à 16:30, aucun week-end |
| `GET /creneaux` avec `au` avant `du` | 422 |

Les créneaux passés sont volontairement absents : utiliser des dates futures.

Tests de `POST /rendez-vous` (corps JSON, dates futures) :

| Cas | Résultat attendu |
|---|---|
| Réservation valide | 201, statut `en_attente`, un `id` (numéro de rendez-vous) |
| Même dentiste, même date et même heure | 409 « Ce créneau vient d'être pris, choisissez-en un autre » |
| Même heure chez un autre dentiste | 201 |
| Samedi ou dimanche | 422 |
| Date dans le passé | 422 |
| Heure `17:00` ou `09:15` | 422 |
| Motif que le dentiste ne propose pas | 422 |
| Téléphone invalide (`12345`) | 422 |
| Dentiste ou motif inexistant | 404 |
| Après annulation du rendez-vous | le créneau redevient réservable |

Le téléphone est accepté avec espaces ou indicatif (`77 123 45 67`, `+221 77 123 45 67`) et stocké sous la forme `771234567`.

---

## 10. Tests unitaires

```bash
pytest
```

Les tests utilisent une base SQLite en mémoire. Ils couvrent les règles métier : double réservation, week-end et créneau passé, motif non proposé, transitions de statut, rappel à 15 minutes, mot de passe, droits d'accès, etc.

---

## 11. Sécurité et qualité

Scan du code et des dépendances (exécuté par Jenkins) :

```bash
bandit -r app
pip-audit -r requirements.txt
```

Bonnes pratiques appliquées :

- aucun secret dans Git (`.env` ignoré, seul `.env.example` est versionné) ;
- mots de passe hachés avec bcrypt ;
- réponses de l'API limitées aux champs utiles (pas de hachage exposé) ;
- validation des entrées côté API.

---

## 12. Docker et CI/CD

À compléter avec les éléments du groupe :

- **Dockerfile** : image Python, démarrage avec
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`, vérification de santé sur `/health`.
- **Jenkinsfile** : checkout, installation des dépendances, tests, scans (bandit, pip-audit), build de l'image, scan Trivy, push sur Docker Hub.
- **Image Docker Hub** : `<compte>/backend:<numéro de build>` et `latest`.

Le backend est **sans état** : il peut tourner en 2 instances derrière Nginx, ce qui permet la mise à jour sans interruption.

---

## 13. Problèmes fréquents

| Erreur | Solution |
|---|---|
| `uvicorn` non reconnu | Activer le `venv`, ou utiliser `python -m uvicorn ...` |
| `No module named 'app'` | Lancer la commande depuis la racine du dépôt (là où se trouve le dossier `app`) |
| `Address already in use` | Ajouter `--port 8001` |
| `GET /dentistes` renvoie `[]` | Supprimer `dentardv.db` puis relancer le serveur |
| Erreur à l'installation de `psycopg2-binary` | Mettre pip à jour : `python -m pip install --upgrade pip` |

---

## 14. Équipe

Groupe : Papa Moussa GUENE, Racine SABALY, Adama SECK, Diegane SECK, Mouhamadou SABALY.

Backend et API : Mouhamadou SABALY.
