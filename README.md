# Big_Data_MLOps_Github_API


créer des fichiers .env dans chaque folder ou se trouve un .env.exemple pour avoir une conf locale

copier le contenu du .env.exemple pour chaque conf locale

créer l'environnnemnt conda en se positionnant à la racine:
``` 
conda env create -f environment.yml
conda activate env_MPT
```


lancer un ```docker compose up --build``` en vérifiant que les ports xxxx,yyyy,zzzz et aaaa sont libres

aller dans le notebook prévu à la démo du projet

lancer un ```docker compose down -v``` pour terminer stopper tous les composants.


