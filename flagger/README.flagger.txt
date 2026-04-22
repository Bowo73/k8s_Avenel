Objectif
  Mettre en place un deploiement progressif (canary) avec Flagger et Traefik,
  en gardant l'acces "stable" existant.

Qu'est ce que Flagger ? A quoi ca sert ?
  Flagger est un operateur Kubernetes (un controller) qui automatise les
  deploiements progressifs. Au lieu de remplacer brutalement une version par
  une autre, Flagger effectue un rollout controle (canary, blue/green, A/B)
  en modifiant progressivement le routage du trafic.

  Dans le mode canary, Flagger:
    - detecte une nouvelle revision (par ex. changement d'image d'un Deployment)
    - deploie une version "canary" a cote de la version "stable" (primary)
    - envoie un faible pourcentage du trafic vers la canary, puis augmente
      par paliers (5%, 10%, ...)
    - observe des indicateurs (taux d'erreur, latence, webhooks de tests)
    - promeut la canary en stable si tout va bien, ou rollback automatiquement
      si les verifications echouent

  L'interet en CI/CD:
    - reduire le risque d'indisponibilite lors d'une mise en production
    - rendre les deploiements repetables et observables (promotion/rollback)
    - integrer des tests (smoke test, load test) dans le processus de rollout

Contexte cible
  - Kubernetes local type kind (Docker Desktop) avec 2 noeuds.
  - Traefik expose sur l'hote via les mappings kind de k8s_Avenel/cluster.yaml:
      HTTP  -> http://<host>:8080
      HTTPS -> https://<host>:8443
  - Application stable accessible via Ingress Kubernetes classique:
      http://skymap.local:8080/

Pourquoi IngressRoute (Traefik CRD) ?
  Flagger (provider Traefik) fait le traffic shifting avec des objets Traefik:
  - IngressRoute
  - TraefikService (weight primary/canary)
  Un Ingress Kubernetes (k8s_Avenel/ingress.yaml) ne permet pas a Flagger de
  gerer des poids de trafic.

Strategie retenue (recommandee pour tester)
  - On garde le stable tel quel sur skymap.local
  - On ajoute un acces canary sur un autre host: canary.skymap.local
  - On deploye une copie des workloads pour le canary (api-cd, frontend-cd)
    afin de ne pas impacter le stable.

Contenu du dossier k8s_Avenel/flagger/
  Infra (YAML renderes, pas besoin de Helm sur la machine cible)
    - 00-traefik-namespace.yaml
    - 01-traefik-rendered.yaml           (Traefik + CRDs + config metrics)
    - 02-flagger-rendered.yaml           (Flagger + CRDs + Prometheus)
    - 03-loadtester-rendered.yaml        (loadtester dans le namespace skymap)

  Stack canary (sans casser le stable)
    - 10-api-cd-deployment.yaml
    - 11-frontend-cd-deployment.yaml
    - 30-canary-ingressroute.yaml        (Host canary.skymap.local)
    - 20-canary-api-cd.yaml
    - 21-canary-frontend-cd.yaml

  Metriques Prometheus (Traefik v3)
    - 42-metrictemplate-traefik-success-rate-api-cd.yaml
    - 43-metrictemplate-traefik-duration-p99-api-cd.yaml
    - 44-metrictemplate-traefik-success-rate-frontend-cd.yaml
    - 45-metrictemplate-traefik-duration-p99-frontend-cd.yaml


Redeployer sur un cluster identique "sans Flagger"

Prerequis machine
  - docker
  - kubectl
  - kind

1) Creer le cluster kind (2 noeuds + ports exposes)
  Depuis la racine du repo:
    kind create cluster --name skymap-cluster --config k8s_Avenel/cluster.yaml
    kubectl config use-context kind-skymap-cluster

2) Construire les images et les charger dans kind
    docker build -t sky_map-api:latest ./sky_map/API
    docker build -t sky_map-frontend:latest ./sky_map/Frontend
    docker pull mariadb:latest

    kind load docker-image sky_map-api:latest --name skymap-cluster
    kind load docker-image sky_map-frontend:latest --name skymap-cluster
    kind load docker-image mariadb:latest --name skymap-cluster

3) Deployer la stack stable (k8s_Avenel)
    kubectl apply -f k8s_Avenel/namespace.yaml
    kubectl apply -f k8s_Avenel/secret.yaml
    kubectl apply -f k8s_Avenel/db.yaml
    kubectl apply -f k8s_Avenel/api.yaml
    kubectl apply -f k8s_Avenel/frontend.yaml
    kubectl apply -f k8s_Avenel/ingress.yaml

  (optionnel) initialiser la base (tables cities/stars)
    kubectl apply -f k8s_Avenel/init-db-job.yaml

4) Configurer les hosts Windows
  Ajouter dans C:\Windows\System32\drivers\etc\hosts (admin):
    127.0.0.1 skymap.local
    127.0.0.1 canary.skymap.local


Activer Flagger (en gardant le stable)

1) Installer Traefik (si pas deja present) + Flagger + Prometheus + loadtester
    kubectl apply -f k8s_Avenel/flagger/00-traefik-namespace.yaml
    kubectl apply -f k8s_Avenel/flagger/01-traefik-rendered.yaml
    kubectl apply -f k8s_Avenel/flagger/02-flagger-rendered.yaml
    kubectl apply -f k8s_Avenel/flagger/03-loadtester-rendered.yaml

2) Deployer la copie canary des workloads
    kubectl apply -f k8s_Avenel/flagger/10-api-cd-deployment.yaml
    kubectl apply -f k8s_Avenel/flagger/11-frontend-cd-deployment.yaml

3) Appliquer les MetricTemplates + Canary + IngressRoute canary
    kubectl apply -f k8s_Avenel/flagger/42-metrictemplate-traefik-success-rate-api-cd.yaml
    kubectl apply -f k8s_Avenel/flagger/43-metrictemplate-traefik-duration-p99-api-cd.yaml
    kubectl apply -f k8s_Avenel/flagger/44-metrictemplate-traefik-success-rate-frontend-cd.yaml
    kubectl apply -f k8s_Avenel/flagger/45-metrictemplate-traefik-duration-p99-frontend-cd.yaml

    kubectl apply -f k8s_Avenel/flagger/20-canary-api-cd.yaml
    kubectl apply -f k8s_Avenel/flagger/21-canary-frontend-cd.yaml
    kubectl apply -f k8s_Avenel/flagger/30-canary-ingressroute.yaml

4) Verifier l'acces
  Stable:
    http://skymap.local:8080/
  Canary:
    http://canary.skymap.local:8080/

5) Declencher un rollout canary
  IMPORTANT: utilise des tags immuables (pas :latest) sinon Flagger peut ne
  pas detecter la nouvelle revision.

  Exemple frontend:
    docker build -t sky_map-frontend:canary1 ./sky_map/Frontend
    kind load docker-image sky_map-frontend:canary1 --name skymap-cluster
    kubectl -n skymap set image deploy/frontend-cd frontend=sky_map-frontend:canary1

  Exemple API:
    docker build -t sky_map-api:canary1 ./sky_map/API
    kind load docker-image sky_map-api:canary1 --name skymap-cluster
    kubectl -n skymap set image deploy/api-cd api=sky_map-api:canary1

6) Suivre le deploiement progressif
    kubectl -n skymap get canary
    kubectl -n skymap describe canary/frontend-cd
    kubectl -n skymap describe canary/api-cd
    kubectl -n traefik logs deploy/flagger -f
