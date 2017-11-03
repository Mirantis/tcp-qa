#!/bin/bash

#. /root/keystonercv3

heat -v --debug stack-create teststack \
  --template-file ../cookied-cicd-queens-dvr-sl/underlay.hot \
  --environment-file microcloud-8116.env \
  --parameters keypair=baremetal
