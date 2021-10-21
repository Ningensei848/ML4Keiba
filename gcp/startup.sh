#! /bin/bash

# caution!! startup-scriptで実行するときの実行ユーザは root
# 相対パスとか効かない

USERNAME=kiai
USERHOME=/home/$USERNAME

GCLOUDSDK_TAG="361.0.0-alpine"
COMPOSE_VERSION="1.29.2"

# `gsutil` でファイルを読み込みたいときは以下のコマンド
# GSUTIL_COMMAND='gsutil -m rsync -r gs://babieca/turtle $USERHOME/data/turtle'
GSUTIL_COMMAND='gsutil --help'

# メタデータに格納したトークンを読み出す
TOKEN_LINE=$(curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/TOKEN_LINE -H "Metadata-Flavor: Google")

LINE_NOTIFY () {
  MSG="[GCE] $1"
  curl -X POST \
    -H "Authorization: Bearer $TOKEN_LINE" \
    -F "message=${MSG}" \
    https://notify-api.line.me/api/notify
}

cd $USERHOME

cat <<-'EOF' > $USERHOME/.bashrc
# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# ctrl+s で出力がロックされてしまうのを防ぐ
stty stop undef

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
. ~/.bash_aliases
fi
EOF


# alias やらファイルコピーやら --------------------------
VAR_PWD='$(pwd)'
VAR_HOME='$HOME'
UID_AND_GID='$(id -u):$(id -g)'
# クォートなしEOFなので，変数は展開されることに注意
cat <<-EOF > $USERHOME/.bash_aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

alias docker-compose='docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$VAR_PWD:$VAR_PWD" \
  -w "$VAR_PWD" \
  docker/compose:$COMPOSE_VERSION'

alias gsutil='docker run --rm -it \
  -v "$VAR_PWD:$VAR_PWD" \
  -v "$VAR_HOME:$VAR_HOME" \
  -v /etc/passwd:/etc/passwd:ro \
  -v /etc/group:/etc/group:ro \
  -v /mnt:/mnt \
  -w $VAR_PWD \
  -u $UID_AND_GID \
  gcr.io/google.com/cloudsdktool/cloud-sdk:latest gsutil'
EOF

# nginx_conf, dotenv, docker_compose の準備 ------------------------
mkdir $USERHOME/nginx
curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/nginx_conf -H "Metadata-Flavor: Google" > $USERHOME/nginx/default.conf.template
curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/dotenv -H "Metadata-Flavor: Google" > $USERHOME/.env
curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/docker_compose -H "Metadata-Flavor: Google" > $USERHOME/docker-compose.yml

# gsutil -m rsync -r src_url dst_url {{{
if [ ! -d $USERHOME/data/turtle ]; then
  mkdir -p $USERHOME/data/turtle
  chown -R $USERNAME:$USERNAME $USERHOME
fi

# 問題：なぜか run 時に一緒に pull すると, unexpected EOF になってコケる
# 対策：一つ前に独立して pull しておく
/usr/bin/docker pull gcr.io/google.com/cloudsdktool/cloud-sdk:$GCLOUDSDK_TAG &> $USERHOME/gsutil_command.log

/usr/bin/docker run --rm -i \
  -v $USERHOME:$USERHOME \
  -v /etc/passwd:/etc/passwd:ro \
  -v /etc/group:/etc/group:ro \
  -v /mnt:/mnt \
  -w $USERHOME \
  -u "$(id $USERNAME -u):$(id $USERNAME -g)" \
  gcr.io/google.com/cloudsdktool/cloud-sdk:$GCLOUDSDK_TAG $GSUTIL_COMMAND &>> $USERHOME/gsutil_command.log ;
# }}}


# docker-compose {{{
/usr/bin/docker  run --rm -i \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$USERHOME:$USERHOME" \
  -w="$USERHOME" \
  docker/compose:$COMPOSE_VERSION up -d ;
# }}}

# 最後に終了通知
LINE_NOTIFY 'startup process completed.'
