#rm -rf .gitignore README.md
cat << EOF > .env
ENVIRONMENT=prod
DRIVER=~websockets
EOF
#echo "$0" > .env.prod