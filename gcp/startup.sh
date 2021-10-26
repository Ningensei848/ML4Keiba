#! /bin/bash

# caution!! startup-scriptで実行するときの実行ユーザは root
# - 相対パスとか効かない
# - 書き込み権限のないディレクトリにいる
# - ファイルに出力したいときは，$USERNAME を使って絶対パスで指定する

# `API_SERVER/${name}` の記述で，instance に付与した metadata にアクセスできる
API_SERVER="http://metadata.google.internal/computeMetadata/v1/instance/attributes"

# metadata: USERNAME
USERNAME=$(curl "$API_SERVER/USERNAME" -H "Metadata-Flavor: Google")
USERHOME=/home/$USERNAME
cd $USERHOME

# metadata: DOTENV -----------------------------------------------------------
curl "$API_SERVER/DOTENV" -H "Metadata-Flavor: Google" > $USERHOME/.env
source $USERHOME/.env
# -----------------------------------------------------------------------------
# これ以降は `.env` 内部に記述した環境変数が使える

# TTLをロードするときに必要なスクリプトを出力 {{{
echo $LOAD_COMMAND > $USERHOME/$LOAD_SCRIPT
chmod u+x $USERHOME/$LOAD_SCRIPT
# }}}


# .env に格納したトークンを読み出す
LINE_NOTIFY () {
  MSG="[GCE] $1"
  curl -X POST \
    -H "Authorization: Bearer $TOKEN_LINE" \
    -F "message=${MSG}" \
    https://notify-api.line.me/api/notify
}

# クォートありEOFなので，変数は展開されない
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
VAR_ARGS='"$@"'

# クォートなしEOFなので，変数は展開されることに注意
cat <<-EOF > $USERHOME/.bash_aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

docker-compose () {
  docker run --rm -it \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$VAR_PWD:$VAR_PWD" \
    -w "$VAR_PWD" \
    docker/compose:$GCE_COMPOSE_TAG $VAR_ARGS ;
}

gsutil () {
  docker run --rm -it \
    -v "$VAR_PWD:$VAR_PWD" \
    -v "$VAR_HOME:$VAR_HOME" \
    -v /etc/passwd:/etc/passwd:ro \
    -v /etc/group:/etc/group:ro \
    -v /mnt:/mnt \
    -w $VAR_PWD \
    -u $UID_AND_GID \
    gcr.io/google.com/cloudsdktool/cloud-sdk:$GCE_SDK_TAG gsutil $VAR_ARGS ;
}

# もし .env があれば，それも読み込む
if [ -f ~/.env ]; then
. ~/.env
fi
EOF

# NGINX {{{
if [ ! -d $USERHOME/nginx ]; then
  mkdir -p $USERHOME/nginx/letsencrypt
  curl "$API_SERVER/NGINX_CONFIG" -H "Metadata-Flavor: Google" > $USERHOME/nginx/default.conf.template
fi
# }}}

# turtle {{{
if [ ! -d $USERHOME/data/turtle ]; then
  mkdir -p $USERHOME/data/turtle
fi
# }}}

# docker-compose {{{
if [ ! -f $USERHOME/docker-compose.yml ]; then
  curl "$API_SERVER/COMPOSE_FILE" -H "Metadata-Flavor: Google" > $USERHOME/docker-compose.yml
fi
# }}}

# このままだと所有権が root のままなので，$USERNAME に移譲する
chown -R $USERNAME:$USERNAME $USERHOME


# 問題：なぜか run 時に一緒に pull すると, unexpected EOF になってコケる
# 対策：一つ前に独立して pull しておく {{{
# cloud-sdk
/usr/bin/docker pull gcr.io/google.com/cloudsdktool/cloud-sdk:$GCE_SDK_TAG &>> $GCE_STARTUP_LOG
# docker-compose
/usr/bin/docker pull docker/compose:$GCE_COMPOSE_TAG &>> $GCE_STARTUP_LOG
# nginx
/usr/bin/docker pull nginx:$NGINX_IMAGE_TAG &>> $GCE_STARTUP_LOG
# openlink/virtuoso-opensource-7
/usr/bin/docker pull openlink/virtuoso-opensource-7:$VIRTUOSO_IMAGE_TAG &>> $GCE_STARTUP_LOG
# certbot/certbot
/usr/bin/docker pull certbot/certbot:$CERTBOT_IMAGE_TAG &>> $GCE_STARTUP_LOG
# }}}

# 関数定義
docker-compose () {
  /usr/bin/docker run --rm -i \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$USERHOME:$USERHOME" \
    -w="$USERHOME" \
    docker/compose:$GCE_COMPOSE_TAG "$@" ;
}

# 証明書がなければ，CERTBOT で証明書を取得する
# nginx なしで 80 ポートを開けて certbot 自身が通信する {{{
if [ ! -d $CERTBOT_VOLUME_PATH/live ]; then
  docker-compose run --rm --publish 80:80 certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --keep \
    --email $USER_EMAIL \
    --no-eff-email \
    -d $SERVER_NAME \
    -d www.$SERVER_NAME ;
fi
# }}}

# docker-compose を起動する：
# ファイルがGCSから同期されていなければ，起動は初回のはず（前提）
# GCSからデータを取得する & ロードもする {{{

docker-compose up -d

if [ ! -f $USERHOME/data/turtle/initialLoader.sql ]; then
  /usr/bin/docker run --rm -i \
    -v $USERHOME:$USERHOME \
    -v /etc/passwd:/etc/passwd:ro \
    -v /etc/group:/etc/group:ro \
    -v /mnt:/mnt \
    -w $USERHOME \
    -u "$(id $USERNAME -u):$(id $USERNAME -g)" \
    gcr.io/google.com/cloudsdktool/cloud-sdk:$GCE_SDK_TAG $GSUTIL_COMMAND &>> $USERHOME/gsutil_command.log ;
    $USERHOME/$LOAD_SCRIPT ;
fi
# }}}

# 最後に終了通知
LINE_NOTIFY 'startup process completed.'
