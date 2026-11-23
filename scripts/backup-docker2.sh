#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 🔄 OMEGA INFORMATIQUE — Script de sauvegarde complet
# ═══════════════════════════════════════════════════════════
# Destination : /mnt/c/dockersep
# Contenu     : Applications, données, uploads, config Docker
# Rotation    : 7 jours (garde les 7 dernières sauvegardes)
# ═══════════════════════════════════════════════════════════

set -e

# ─── Configuration ───
SOURCE_DIR="/home/momo/docker2"
BACKUP_ROOT="/mnt/c/dockersep"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/omega-backup-${TIMESTAMP}"
LOG_FILE="${BACKUP_ROOT}/backup.log"

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# ─── Fonctions ───
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

# ─── Démarrage ───
echo "═══════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "🔄 OMEGA INFORMATIQUE — SAUVEGARDE" | tee -a "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
log "Timestamp : $TIMESTAMP"
log "Source    : $SOURCE_DIR"
log "Destination : $BACKUP_DIR"
echo ""

# ─── Vérifications préalables ───
if [ ! -d "$SOURCE_DIR" ]; then
    log_error "Répertoire source introuvable : $SOURCE_DIR"
    exit 1
fi

if [ ! -d "$BACKUP_ROOT" ]; then
    log_warn "Répertoire de sauvegarde inexistant. Création..."
    mkdir -p "$BACKUP_ROOT"
fi

# Vérifier l'espace disque (besoin de ~5 GB minimum)
AVAILABLE=$(df "$BACKUP_ROOT" | tail -1 | awk '{print $4}')
AVAILABLE_GB=$((AVAILABLE / 1024 / 1024))
if [ "$AVAILABLE_GB" -lt 5000 ]; then
    log_warn "Espace disque faible : ${AVAILABLE_GB} MB disponibles"
fi

log "Espace disponible : ${AVAILABLE_GB} MB"
echo ""

# ─── Création du répertoire de sauvegarde ───
mkdir -p "$BACKUP_DIR"
cd "$SOURCE_DIR"

# ─── 1. Sauvegarde des applications ───
log "📦 1. Sauvegarde des applications..."
mkdir -p "$BACKUP_DIR/apps"
rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
      "$SOURCE_DIR/apps/" "$BACKUP_DIR/apps/" 2>&1 | grep -v "^$" || true
APP_COUNT=$(find "$BACKUP_DIR/apps" -maxdepth 1 -type d | tail -n +2 | wc -l)
log_success "$APP_COUNT applications sauvegardées"

# ─── 2. Sauvegarde des données (bases SQLite) ───
log ""
log "💾 2. Sauvegarde des bases de données..."
mkdir -p "$BACKUP_DIR/data"

# Arrêter temporairement les conteneurs pour une sauvegarde cohérente des DB
log "   ⏸️  Pause des conteneurs pour cohérence des bases..."
docker ps --filter "name=docker2_" --format "{{.Names}}" | while read c; do
    docker pause "$c" >/dev/null 2>&1 || true
done

# Copier les bases
rsync -a "$SOURCE_DIR/data/" "$BACKUP_DIR/data/" 2>&1 | grep -v "^$" || true
DB_COUNT=$(find "$BACKUP_DIR/data" -name "*.db" | wc -l)
log_success "$DB_COUNT bases de données sauvegardées"

# Reprendre les conteneurs
log "   ▶️  Reprise des conteneurs..."
docker ps -a --filter "name=docker2_" --format "{{.Names}}" | while read c; do
    docker unpause "$c" >/dev/null 2>&1 || true
done

# ─── 3. Sauvegarde des uploads ───
log ""
log "📸 3. Sauvegarde des uploads (photos, documents)..."
mkdir -p "$BACKUP_DIR/uploads"
if [ -d "$SOURCE_DIR/uploads" ]; then
    rsync -a "$SOURCE_DIR/uploads/" "$BACKUP_DIR/uploads/" 2>&1 | grep -v "^$" || true
    UP_SIZE=$(du -sh "$BACKUP_DIR/uploads" | cut -f1)
    log_success "Uploads sauvegardés ($UP_SIZE)"
else
    log_warn "Aucun dossier uploads"
fi

# ─── 4. Sauvegarde de la configuration ───
log ""
log "⚙️  4. Sauvegarde de la configuration..."
mkdir -p "$BACKUP_DIR/config"

# docker-compose.yml
cp "$SOURCE_DIR/docker-compose.yml" "$BACKUP_DIR/config/" 2>/dev/null || true

# Nginx configs
if [ -d "$SOURCE_DIR/nginx" ]; then
    cp -r "$SOURCE_DIR/nginx" "$BACKUP_DIR/config/" 2>/dev/null || true
fi

# Portal
if [ -d "$SOURCE_DIR/portal" ]; then
    cp -r "$SOURCE_DIR/portal" "$BACKUP_DIR/config/" 2>/dev/null || true
fi

# Scripts
if [ -d "$SOURCE_DIR/scripts" ]; then
    cp -r "$SOURCE_DIR/scripts" "$BACKUP_DIR/config/" 2>/dev/null || true
fi

# Scripts utilitaires
for f in start-all.sh check-restart-policies.sh clean-docker.sh fix-restart-policies.sh; do
    [ -f "$SOURCE_DIR/$f" ] && cp "$SOURCE_DIR/$f" "$BACKUP_DIR/config/"
done

# .env si présent
[ -f "$SOURCE_DIR/.env" ] && cp "$SOURCE_DIR/.env" "$BACKUP_DIR/config/"

log_success "Configuration sauvegardée"

# ─── 5. Manifeste des images Docker ───
log ""
log "🐳 5. Génération du manifeste Docker..."
{
    echo "# ═══════════════════════════════════════════════════════════"
    echo "# OMEGA — Manifeste Docker"
    echo "# Date : $(date '+%Y-%m-%d %H:%M:%S')"
    echo "# ═══════════════════════════════════════════════════════════"
    echo ""
    echo "## Images Docker"
    echo ""
    docker images --format "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}" | grep "docker2-" | sort
    echo ""
    echo "## Conteneurs actifs"
    echo ""
    docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}" | sort
    echo ""
    echo "## Politiques de redémarrage"
    echo ""
    docker ps -a --format "{{.Names}}" | sort | while read c; do
        policy=$(docker inspect "$c" --format='{{.HostConfig.RestartPolicy.Name}}' 2>/dev/null)
        echo "$c : $policy"
    done
    echo ""
    echo "## Volumes Docker"
    echo ""
    docker volume ls
    echo ""
    echo "## Version Docker"
    echo ""
    docker --version
    docker compose version
} > "$BACKUP_DIR/config/DOCKER-MANIFEST.txt"

log_success "Manifeste Docker généré"

# ─── 6. Métadonnées de sauvegarde ───
cat > "$BACKUP_DIR/BACKUP-INFO.txt" << EOF
═══════════════════════════════════════════════════════════
🔐 OMEGA INFORMATIQUE — Sauvegarde
═══════════════════════════════════════════════════════════

Date          : $(date '+%Y-%m-%d %H:%M:%S')
Timestamp     : $TIMESTAMP
Hôte          : $(hostname)
Utilisateur   : $(whoami)
Système       : $(uname -a)

📊 CONTENU :
  • Applications    : $APP_COUNT
  • Bases données   : $DB_COUNT
  • Uploads         : $UP_SIZE
  • Configuration   : docker-compose.yml + nginx + scripts

🔄 RESTAURATION :
  bash ~/docker2/scripts/restore-docker2.sh $BACKUP_DIR

📞 Support : contact@omega-consulting.sn
═══════════════════════════════════════════════════════════
EOF

# ─── 7. Compression (optionnel) ───
log ""
log "🗜️  7. Compression de la sauvegarde..."
cd "$BACKUP_ROOT"
ARCHIVE_NAME="omega-backup-${TIMESTAMP}.tar.gz"

if command -v pigz >/dev/null 2>&1; then
    tar --use-compress-program=pigz -cf "$ARCHIVE_NAME" "omega-backup-${TIMESTAMP}/"
else
    tar -czf "$ARCHIVE_NAME" "omega-backup-${TIMESTAMP}/"
fi

ARCHIVE_SIZE=$(du -h "$ARCHIVE_NAME" | cut -f1)
log_success "Archive créée : $ARCHIVE_NAME ($ARCHIVE_SIZE)"

# Supprimer le dossier non compressé
rm -rf "$BACKUP_DIR"

# ─── 8. Rotation (garder les 7 derniers) ───
log ""
log "🔄 8. Rotation des sauvegardes (garder les 7 dernières)..."

cd "$BACKUP_ROOT"
ls -1t omega-backup-*.tar.gz 2>/dev/null | tail -n +8 | while read old; do
    log "   🗑️  Suppression : $old"
    rm -f "$old"
done

BACKUP_COUNT=$(ls -1 omega-backup-*.tar.gz 2>/dev/null | wc -l)
log_success "$BACKUP_COUNT sauvegardes conservées"

# ─── 9. Rapport final ───
echo ""
echo "═══════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "✅ SAUVEGARDE TERMINÉE" | tee -a "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo ""
log "📁 Archive : $BACKUP_ROOT/$ARCHIVE_NAME"
log "📊 Taille  : $ARCHIVE_SIZE"
log "🕐 Durée   : $(date '+%H:%M:%S')"
echo ""
log "Pour restaurer :"
log "  bash ~/docker2/scripts/restore-docker2.sh $BACKUP_ROOT/$ARCHIVE_NAME"
echo ""

# ─── 10. Détail des sauvegardes ───
echo "📋 Historique des sauvegardes :"
ls -lht "$BACKUP_ROOT"/omega-backup-*.tar.gz 2>/dev/null | head -10 | awk '{print "  " $9 " (" $5 ")"}'
echo ""

