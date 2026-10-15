#!/usr/bin/env bash
# Install the external tools js-analyze prefers. No sudo required (installs into
# user-writable go/bin, npm-global, and pipx). Safe to re-run (idempotent-ish).
set +e
echo "[*] Installing js-analyze toolchain into user space..."

have() { command -v "$1" >/dev/null 2>&1; }

# --- Secrets ---
if ! have trufflehog; then
  echo "[*] trufflehog"
  curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh \
    | sh -s -- -b "$HOME/.local/bin"
fi
have gitleaks || echo "[!] gitleaks missing (install via distro pkg)"

# --- JS endpoint/param extraction (AST) ---
if ! have jsluice; then
  echo "[*] jsluice"
  go install github.com/BishopFox/jsluice/cmd/jsluice@latest
fi

# --- Link/endpoint regex extraction ---
if ! have linkfinder; then
  echo "[*] LinkFinder"
  pipx install git+https://github.com/GerbenJavado/LinkFinder.git 2>/dev/null \
    || pip install --user --break-system-packages \
         git+https://github.com/GerbenJavado/LinkFinder.git
fi
if ! have xnLinkFinder; then
  echo "[*] xnLinkFinder"
  pipx install xnLinkFinder 2>/dev/null
fi

# --- Vulnerable library detection (CVEs) ---
if ! have retire; then
  echo "[*] retire.js"
  npm install -g retire
fi

# --- JS collection ---
have getJS  || { echo "[*] getJS";  go install github.com/003random/getJS@latest; }
have subjs  || { echo "[*] subjs";  go install github.com/lc/subjs@latest; }
have waymore || { echo "[*] waymore"; pipx install waymore 2>/dev/null; }

# --- Secrets in JS (regex, JS-focused) ---
have mantra || { echo "[*] mantra"; go install github.com/MrEmpy/mantra@latest 2>/dev/null; }

echo
echo "[*] Verify:"
for t in trufflehog gitleaks jsluice linkfinder xnLinkFinder retire getJS subjs waymore mantra katana gau nuclei semgrep; do
  command -v "$t" >/dev/null 2>&1 && echo "  ok   $t" || echo "  MISS $t"
done
echo "[*] Ensure \$HOME/.local/bin and \$(go env GOPATH)/bin are on PATH."
