#!/bin/bash
# Déploiement rapide sans rebuild
echo "🚀 Déploiement AgriSénégal..."
docker cp ~/docker2/apps/agri/main.py docker2_agri:/app/main.py
docker cp ~/docker2/apps/agri/auth.py docker2_agri:/app/auth.py
docker cp ~/docker2/apps/agri/crud.py docker2_agri:/app/crud.py
docker cp ~/docker2/apps/agri/agri_logic.py docker2_agri:/app/agri_logic.py
docker cp ~/docker2/apps/agri/agri_ia.py docker2_agri:/app/agri_ia.py
docker restart docker2_agri
echo "✅ Redéployé !"
