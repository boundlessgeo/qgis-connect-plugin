#!/bin/bash
# Run the tests locally using the qgis testing environment docker

xhost +

PLUGIN_NAME="boundlessconnect"
# One of master_2, master, release
TARGET_VERSION=master

if [ $TARGET_VERSION = 'master' ]; then
    PIP_EXECUTABLE=pip3
else
    PIP_EXECUTABLE=pip
fi

#docker rm -f qgis-testing-environment

# replace latest with master if you wish to test on master, latest is
# latest supported Boundless release
docker pull boundlessgeo/qgis-testing-environment:$TARGET_VERSION
docker tag boundlessgeo/qgis-testing-environment:$TARGET_VERSION qgis-testing-environment

docker run -d  --name qgis-testing-environment  -e DISPLAY=:99 -v /tmp/.X11-unix:/tmp/.X11-unix -v `pwd`:/tests_directory qgis-testing-environment

# Setup
docker exec -it qgis-testing-environment sh -c "qgis_setup.sh $PLUGIN_NAME"
docker exec -it qgis-testing-environment sh -c "$PIP_EXECUTABLE install paver"
PLUGIN_VERSION=`grep version $PLUGIN_NAME/metadata.txt | perl -npe 's/[^\d-]//g'`
docker exec -it qgis-testing-environment sh -c "mkdir -p /root/.config/Boundless; printf \"[General]\n\" >> /root/.config/Boundless/BoundlessConnect.conf"
docker exec -it qgis-testing-environment sh -c "printf  \"firstRun${PLUGIN_VERSION}=false\nfirstRun=false\n\n\" >> /root/.config/Boundless/BoundlessConnect.conf"

# Package
docker exec -it qgis-testing-environment sh -c "cd /tests_directory && paver setup && paver package --tests"

# Run tests
docker exec -it qgis-testing-environment sh -c "qgis_testrunner.sh ${PLUGIN_NAME}.tests.testerplugin.run_tests"
