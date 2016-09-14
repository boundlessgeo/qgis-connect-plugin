#!/bin/bash
# Run the tests locally using the qgis testing environment docker

xhost +

PLUGIN_NAME="boundlessconnect"

docker rm -f qgis-testing-environment

# replace latest with master if you wish to test on master, latest is
# latest supported Boundless release
docker pull elpaso/qgis-testing-environment:master
docker tag elpaso/qgis-testing-environment:master qgis-testing-environment

docker run -d  --name qgis-testing-environment  -e DISPLAY=:99 -v /tmp/.X11-unix:/tmp/.X11-unix -v `pwd`:/tests_directory qgis-testing-environment


docker exec -it qgis-testing-environment sh -c "qgis_setup.sh $PLUGIN_NAME"

# Install the plugin
docker exec -it qgis-testing-environment sh -c "easy_install --upgrade pip"
docker exec -it qgis-testing-environment sh -c "pip install paver"
docker exec -it qgis-testing-environment sh -c "cd /tests_directory && paver setup"
docker exec -it qgis-testing-environment sh -c "mkdir -p /root/.qgis2/python/plugins/"
docker exec -it qgis-testing-environment sh -c "ln -s /tests_directory/$PLUGIN_NAME /root/.qgis2/python/plugins/$PLUGIN_NAME"

# Disable first run wizard
PLUGIN_VERSION=`grep version $PLUGIN_NAME/metadata.txt | perl -npe 's/[^\d-]//g'`
docker exec -it qgis-testing-environment sh -c "mkdir -p /root/.config/Boundless; printf \"[General]\n\" >> /root/.config/Boundless/BoundlessConnect.conf"
docker exec -it qgis-testing-environment sh -c "printf  \"firstRun${PLUGIN_VERSION}=false\n\n\" >> /root/.config/Boundless/BoundlessConnect.conf"


# run the tests
docker exec -it qgis-testing-environment sh -c "DISPLAY=unix:0 qgis_testrunner.sh $PLUGIN_NAME.tests.testerplugin.run_tests"
