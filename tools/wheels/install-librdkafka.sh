#!/bin/bash

set -ex

VER="$1"
DEST="$2"

if [[ -z $DEST ]]; then
    echo "Usage: $0 <librdkafka-redist-version> <destdir>"
    exit 1
fi

if [[ -f $DEST/build/native/include/librdkafka/rdkafka.h ]]; then
    echo "$0: librdkafka already installed in $DEST"
    exit 0
fi

echo "$0: Installing librdkafka $VER to $DEST"
[[ -d "$DEST" ]] || mkdir -p "$DEST"
pushd "$DEST"

# Check if variable exists
if [ -z "${GITHUB_TOKEN}" ]; then
    echo "Error: GITHUB_TOKEN is not set"
    exit 1
fi

curl -H "Authorization: Bearer ${GITHUB_TOKEN}" \
 -H "Accept: application/vnd.github.v3+json" \
 -L \
 -o lrk$VER.zip \
https://nuget.pkg.github.com/G-Research/download/librdkafka.redist/$VER/librdkafka.redist.$VER.nupkg

#curl -L -o lrk$VER.zip https://www.nuget.org/api/v2/package/librdkafka.redist/$VER

unzip lrk$VER.zip

ARCH=${ARCH:-x64}

if [[ $OSTYPE == linux* ]]; then
    # Linux
    LIBDIR=runtimes/linux-$ARCH/native

    # Copy the librdkafka build with least dependencies to librdkafka.so.1
    if [[ $ARCH == arm64* ]]; then
        cp -v $LIBDIR/{librdkafka.so,librdkafka.so.1}
    else
        cp -v $LIBDIR/{centos8-librdkafka.so,librdkafka.so.1}
        # Copy the librdkafka build with sasl2 support to 2 versions:
        # librdkafka_sasl2_2.so.1 for debian-based distros
        # librdkafka_sasl2_3.so.1 for rpm-based distros
        patchelf --set-soname librdkafka_sasl2_2.so.1 --output $LIBDIR/{librdkafka_sasl2_2.so.1,librdkafka.so}
        patchelf --replace-needed libsasl2.so.3 libsasl2.so.2 $LIBDIR/librdkafka_sasl2_2.so.1
        ln -s librdkafka_sasl2_2.so.1 $LIBDIR/librdkafka_sasl2_2.so
        patchelf --set-soname librdkafka_sasl2_3.so.1 --output $LIBDIR/{librdkafka_sasl2_3.so.1,librdkafka.so}
        ln -s librdkafka_sasl2_3.so.1 $LIBDIR/librdkafka_sasl2_3.so
    fi
    for lib in $LIBDIR/librdkafka*.so.1; do
        echo $lib
        ldd $lib
    done

elif [[ $OSTYPE == darwin* ]]; then
    # MacOS X

    # Change the library's self-referencing name from
    # /Users/travis/.....somelocation/librdkafka.1.dylib to its local path.
    install_name_tool -id $PWD/runtimes/osx-$ARCH/native/librdkafka.dylib runtimes/osx-$ARCH/native/librdkafka.dylib

    otool -L runtimes/osx-$ARCH/native/librdkafka.dylib
fi

popd
