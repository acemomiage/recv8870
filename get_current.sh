#!/bin/bash

if [ -S /tmp/pmeasure.sock ]; then
  socat stdout /tmp/pmeasure.sock
fi

