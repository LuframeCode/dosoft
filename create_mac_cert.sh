#!/usr/bin/env bash
# ============================================================
#  DOSOFT - Création d'un certificat de signature local (macOS)
#
#  macOS rattache l'autorisation « Accessibilité » à la signature de l'app.
#  Signée « ad hoc », chaque build a une identité différente et doit être
#  ré-autorisé. Avec ce certificat auto-signé, build_mac.sh signe toujours
#  avec la même identité : l'autorisation survit aux nouveaux builds.
#
#  Usage : ./create_mac_cert.sh            (crée « Dosoft Dev » une seule fois)
#  Variables : DOSOFT_CERT_NAME, DOSOFT_KEYCHAIN
# ============================================================
set -euo pipefail

NAME="${DOSOFT_CERT_NAME:-Dosoft Dev}"
KEYCHAIN="${DOSOFT_KEYCHAIN:-$HOME/Library/Keychains/login.keychain-db}"
OPENSSL=/usr/bin/openssl   # LibreSSL d'Apple : PKCS#12 compatible avec `security import`

# Autorise codesign à utiliser la clé sans boîte de dialogue. Sans cette étape,
# macOS demande le mot de passe du trousseau pour CHAQUE fichier signé du bundle.
authorize_codesign() {
    echo "[*] Autorisation de codesign sur la clé « $NAME »."
    if [ -n "${DOSOFT_KEYCHAIN_PASSWORD:-}" ]; then
        security set-key-partition-list -S apple-tool:,apple:,codesign: -s -l "$NAME" \
            -k "$DOSOFT_KEYCHAIN_PASSWORD" "$KEYCHAIN" >/dev/null
    else
        echo "    Saisissez le mot de passe de votre session macOS (celui du trousseau) :"
        security set-key-partition-list -S apple-tool:,apple:,codesign: -s -l "$NAME" "$KEYCHAIN" >/dev/null
    fi
    echo "[OK] codesign peut signer avec « $NAME » sans boîte de dialogue."
}

if security find-identity -p codesigning "$KEYCHAIN" 2>/dev/null | grep -q "\"$NAME\""; then
    echo "[OK] Le certificat « $NAME » existe déjà dans $KEYCHAIN"
    authorize_codesign
    exit 0
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=$("$OPENSSL" rand -hex 16)

cat > "$TMP/cert.cnf" <<EOF
[req]
distinguished_name = dn
x509_extensions = ext
prompt = no
[dn]
CN = $NAME
[ext]
basicConstraints = critical, CA:false
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, codeSigning
subjectKeyIdentifier = hash
EOF

echo "[*] Génération du certificat « $NAME » (10 ans)..."
"$OPENSSL" req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -config "$TMP/cert.cnf" -keyout "$TMP/key.pem" -out "$TMP/cert.pem" 2>/dev/null
"$OPENSSL" pkcs12 -export -inkey "$TMP/key.pem" -in "$TMP/cert.pem" \
    -name "$NAME" -passout "pass:$PASS" -out "$TMP/cert.p12" 2>/dev/null

echo "[*] Import dans le trousseau $KEYCHAIN..."
security import "$TMP/cert.p12" -k "$KEYCHAIN" -P "$PASS" -T /usr/bin/codesign >/dev/null
authorize_codesign

echo
echo "[OK] Certificat « $NAME » créé."
echo "     Les prochains ./build_mac.sh signeront DOSOFT avec ce certificat."
