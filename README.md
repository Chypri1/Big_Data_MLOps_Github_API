# Big_Data_MLOps_Github_API

## REFAIRE CE README 

changer le mode commenté entre ligne 152 et 161 dans ./api-request-github/appelGithub.py

créer des ficheirs .env dans chaque folder ou se trouve un .env.exemple pour avoir une conf locale
copier le contenu du .env.exemple pour chaque conf locale

créer l'environnnemnt conda en se positionnant à la racine:
``` 
conda env create -f environment.yml
conda activate mon_environnement
```


lancer un ```docker compose up --build``` en vérifiant que les ports xxxx,yyyy,zzzz et aaaa sont libres

aller dans le notebook prévu à la démo du projet (si besoin un notebook par folder est dispo pour tester chaque endpoint créé)

lancer un ```docker compose down -v``` pour terminer stopper tous les composants.


