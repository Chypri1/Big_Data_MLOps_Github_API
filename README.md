# Big_Data_MLOps_Github_API


créer des fichiers .env dans chaque folder ou se trouve un .env.exemple pour avoir une conf locale

copier le contenu du .env.exemple pour chaque conf locale

créer l'environnnemnt conda en se positionnant à la racine:
``` 
conda env create -f environnement.yml
conda activate env_MPT
```

Cet environnement conda sert à lancer les différents notebook du projet.


lancer un ```docker compose up --build``` en vérifiant que les ports:
- 2181,
- 7000,
- 8080, 
- 8081, 
- 8083, 
- 8083, 
- 8084,
- 8085,
- 9092,
- 27017 et sont libres

aller dans le notebook prévu à la démo du projet
Il faut savoir que certains composants comme api-base-mongo, api-request-github et la base mongodb étaient sur Azure. 
Ces ressources ne sont plus accessible du aux credentials qui ont expirés.

lancer un ```docker compose down -v``` pour terminer stopper tous les composants.


