#!/usr/bin/env bash

set -u

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

print_header() {
  printf "\n== %s ==\n" "$1"
}

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf "[PASS] %s\n" "$1"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  printf "[WARN] %s\n" "$1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf "[FAIL] %s\n" "$1"
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

version_line() {
  "$@" 2>/dev/null | head -n 1
}

print_header "Linux Mint GNOME Developer System Check"
printf "Host: %s\n" "$(hostname 2>/dev/null || printf unknown)"
printf "Date: %s\n" "$(date '+%Y-%m-%d %H:%M:%S %Z')"
printf "Shell: %s\n" "${SHELL:-unknown}"
printf "Desktop: %s\n" "${XDG_CURRENT_DESKTOP:-unknown}"

print_header "Git"
if has_command git; then
  pass "git installed: $(version_line git --version)"
  GIT_NAME=$(git config --global --get user.name || true)
  GIT_EMAIL=$(git config --global --get user.email || true)
  if [ -n "$GIT_NAME" ]; then
    pass "git user.name: $GIT_NAME"
  else
    warn "git user.name is not set"
  fi
  if [ -n "$GIT_EMAIL" ]; then
    pass "git user.email: $GIT_EMAIL"
  else
    warn "git user.email is not set"
  fi
else
  fail "git is not installed"
fi

print_header "Docker"
if has_command docker; then
  pass "docker installed: $(version_line docker --version)"
  if docker info >/dev/null 2>&1; then
    pass "docker daemon is reachable"
    if docker image inspect hello-world:latest >/dev/null 2>&1; then
      if docker run --rm hello-world >/dev/null 2>&1; then
        pass "docker can run containers"
      else
        warn "docker daemon works, but hello-world container failed"
      fi
    else
      warn "docker daemon works; hello-world image is not available locally, skipping run test"
    fi
  else
    fail "docker daemon is not reachable or current user lacks permission"
  fi
else
  fail "docker is not installed"
fi

print_header "Node.js / npm"
if has_command node; then
  pass "node installed: $(version_line node --version)"
else
  fail "node is not installed"
fi

if has_command npm; then
  pass "npm installed: $(version_line npm --version)"
else
  fail "npm is not installed"
fi

print_header "Python"
if has_command python3; then
  pass "python3 installed: $(version_line python3 --version)"
else
  fail "python3 is not installed"
fi

if has_command pip3; then
  pass "pip3 installed: $(version_line pip3 --version)"
elif python3 -m pip --version >/dev/null 2>&1; then
  pass "pip installed: $(version_line python3 -m pip --version)"
else
  fail "pip for python3 is not installed"
fi

print_header "VS Code"
if has_command code; then
  pass "VS Code CLI installed: $(version_line code --version)"
elif dpkg -s code >/dev/null 2>&1; then
  pass "VS Code package is installed"
else
  fail "VS Code is not installed or 'code' is not in PATH"
fi

print_header "Codex CLI"
if has_command codex; then
  CODEX_VERSION=$(codex --version 2>/dev/null | head -n 1 || true)
  if [ -n "$CODEX_VERSION" ]; then
    pass "codex installed: $CODEX_VERSION"
  else
    pass "codex command exists"
  fi
else
  fail "codex CLI is not installed"
fi

print_header "Shell"
CURRENT_SHELL=$(basename "${SHELL:-}")
LOGIN_SHELL=$(getent passwd "$USER" 2>/dev/null | cut -d: -f7)
LOGIN_SHELL_NAME=$(basename "$LOGIN_SHELL")
if [ "$CURRENT_SHELL" = "zsh" ] && [ "$LOGIN_SHELL_NAME" = "zsh" ]; then
  pass "zsh is current and default shell"
elif [ "$LOGIN_SHELL_NAME" = "zsh" ]; then
  warn "zsh is default shell, but current shell is ${CURRENT_SHELL:-unknown}"
else
  fail "default shell is ${LOGIN_SHELL:-unknown}, not zsh"
fi

print_header "GitHub SSH"
if has_command ssh; then
  SSH_OUTPUT=$(ssh -T -o BatchMode=yes -o ConnectTimeout=10 git@github.com 2>&1)
  SSH_STATUS=$?
  if printf "%s" "$SSH_OUTPUT" | grep -qi "successfully authenticated"; then
    pass "GitHub SSH authentication works"
  elif [ "$SSH_STATUS" -eq 1 ] && printf "%s" "$SSH_OUTPUT" | grep -qi "does not provide shell access"; then
    pass "GitHub SSH authentication works"
  elif printf "%s" "$SSH_OUTPUT" | grep -Eqi "Could not resolve hostname|Name or service not known|Connection timed out|Network is unreachable"; then
    warn "GitHub SSH could not be checked because network/DNS is unavailable: $SSH_OUTPUT"
  else
    fail "GitHub SSH authentication failed: $SSH_OUTPUT"
  fi
else
  fail "ssh is not installed"
fi

print_header "Summary"
printf "PASS: %d  WARN: %d  FAIL: %d\n" "$PASS_COUNT" "$WARN_COUNT" "$FAIL_COUNT"

if [ "$FAIL_COUNT" -gt 0 ]; then
  exit 1
fi

if [ "$WARN_COUNT" -gt 0 ]; then
  exit 2
fi

exit 0
