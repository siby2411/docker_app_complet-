#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 🔄 OMEGA INFORMATIQUE — Script de restauration
# ═══════════════════════════════════════════════════════════

set -e

ARCHIVE="$1"
TARGET_DIR="/home/momo/docker2"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ -z "$ARCHIVE" ] || [ ! -f "$ARCHIVE" ]; then
    echo -e "${RED}❌ Usage : $0 <archive.tar.gz>${NC}"
    echo ""
    echo "Sauvegardes disponibles :"
    ls -lht /mnt/c/dockersep/omega-backup-*.tar.gz 2>/dev/null | head -10
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔄 RESTAURATION OMEGA${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}⚠️  ATTENTION : Cette opération va remplacer les données actuelles${NC}"
echo "Archive : $ARCHIVE"
echo "Cible   : $TARGET_DIR"
echo ""
read -p "Confirmer la restauration ? (oui/non) : " CONFIRM

if [ "$CONFIRM" != "oui" ]; then
    echo "Annulé."
    exit 0
fi

# Sauvegarder l'état actuel
echo ""
echo -e "${BLUE}💾 Sauvegarde de l'état actuel...${NC}"
BACKUP_BEFORE="/mnt/c/dockersep/before-restore-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_BEFORE"
cp -r "$TARGET_DIR" "$BACKUP_BEFORE/docker2-avant-restauration" 2>/dev/null || true
echo -e "${GREEN}✅ Backup pré-restauration : $BACKUP_BEFORE${NC}"

# Arrêter les conteneurs
echo ""
echo -e "${BLUE}⏸️  Arrêt des conteneurs...${NC}"
cd "$TARGET_DIR"
docker compose down 2>&1 | tail -5 || true

# Extraire l'archive
echo ""
echo -e "${BLUE}📦 Extraction de l'archive...${NC}"
TEMP_DIR="/tmp/omega-restore-$$"
mkdir -p "$TEMP_DIR"
tar -xzf "$ARCHIVE" -C "$TEMP_DIR"

EXTRACTED=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "omega-backup-*" | head -1)

if [ -z "$EXTRACTED" ]; then
    echo -e "${RED}❌ Archive invalide${NC}"
    exit 1
fi

# Restaurer
echo ""
echo -e "${BLUE}🔄 Restauration des fichiers...${NC}"

# Applications
rsync -a --delete "$EXTRACTED/apps/" "$TARGET_DIR/apps/" 2>/dev/null || true
echo "  ✅ Applications"

# Data
rsync -a --delete "$EXTRACTED/data/" "$TARGET_DIR/data/" 2>/dev/null || true
echo "  ✅ Données"

# Uploads
rsync -a --delete "$EXTRACTED/uploads/" "$TARGET_DIR/uploads/" 2>/dev/null || true
echo "  ✅ Uploads"

# Config
cp "$EXTRACTED/config/docker-compose.yml" "$TARGET_DIR/" 2>/dev/null || true
[ -d "$EXTRACTED/config/nginx" ] && cp -r "$EXTRACTED/config/nginx" "$TARGET_DIR/"
[ -d "$EXTRACTED/config/portal" ] && cp -r "$EXTRACTED/config/portal" "$TARGET_DIR/"
[ -d "$EXTRACTED/config/scripts" ] && cp -r "$EXTRACTED/config/scripts" "$TARGET_DIR/"
echo "  ✅ Configuration"

# Nettoyer
rm -rf "$TEMP_DIR"

# Redémarrer
echo ""
echo -e "${BLUE}🚀 Redémarrage des services...${NC}"
docker compose up -d --no-build \
    nginx-proxy duckdns-updater \
    ecole clinique ecommerce stock commerciale pos pointage rh \
    projets ged hotel pointage_v2 transport agri agro microfinance \
    pharmacie transport_v2 crm btp marketplace assurance formation_pro \
    immobilier restaurant telemedecine mode auto parts 2>&1 | tail -10

sleep 30

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ RESTAURATION TERMINÉE${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "▸ Conteneurs actifs : $(docker ps -q | wc -l)"
echo "▸ Test : curl http://localhost:9030/health"
echo ""
