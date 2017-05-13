#!/bin/bash
BINARY="./mailinglistbot.pex"
rm -f $BINARY
pex -r requirements.txt -e mailinglistbot:run -o $BINARY ./ && echo "OK, $BINARY created"

