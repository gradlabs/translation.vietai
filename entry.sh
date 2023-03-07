#!/bin/bash

python app.py worker -l INFO --without-web &
tail -f /dev/null
