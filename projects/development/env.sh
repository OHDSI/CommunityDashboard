if [ -n "$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN" ]; then
  export NG_ALLOWED_HOSTS="--allowed-hosts ${CODESPACE_NAME}-4200.$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"
  gh codespace ports visibility 5001:public -c $CODESPACE_NAME # https://github.com/community/community/discussions/15351
fi