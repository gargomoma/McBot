#!/bin/sh

git filter-branch --env-filter '
export GIT_COMMITTER_NAME="Zebstrika"
export GIT_COMMITTER_EMAIL="zebstrika@horsefucker.org"
export GIT_AUTHOR_NAME="$GIT_COMMITTER_NAME"
export GIT_AUTHOR_EMAIL="$GIT_COMMITTER_EMAIL"
' --tag-name-filter cat -- --branches --tags
