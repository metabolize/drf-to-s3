#!/bin/bash
#
# Fetches the given version of Fine Uploader and builds it into dist/.
#

REMOTE=https://github.com/Widen/fine-uploader.git
SRC=vendor/fine-uploader
TARGET=drf_to_s3/integration/static/fine-uploader

if [ $# -ne 1 ]; then
    echo "Usage: $0 version"
    echo
    echo "Here are a few recent versions:"
    echo
    git ls-remote --tags https://github.com/Widen/fine-uploader.git | sed -e 's/.*refs\/tags\/\([0-9.]*\).*/     \1/' | sort -n -r | uniq | head -5
    echo
    exit 1
fi

rm -rf $SRC $TARGET

echo
echo Downloading version $1
echo

mkdir -p $SRC
if [[ `git --version` < 'git version 1.9' ]]; then
    git clone $REMOTE $SRC &&
    (cd $SRC && git checkout $1) || exit 1
else
    git clone --branch $1 --single-branch $REMOTE $SRC || exit 1    
fi

(cd $SRC &&
npm install &&
grunt package) || exit 1

mkdir -p $TARGET &&
find $SRC/_dist -mindepth 1 -maxdepth 1 -type d -exec cp -r {} $TARGET \; &&
# Remove all the version numbers
find $TARGET -mindepth 1 -maxdepth 1 -name "*-$1*" -exec bash -c "mv \$0 \${0/-$1/}" {} \; &&
find $TARGET -name "*-$1*" -exec bash -c "mv \$0 \${0/-$1/}" {} \; || exit 1

echo
echo Successfully built version $1
echo
