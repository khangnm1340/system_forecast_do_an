#!/usr/bin/env bash

STATE_FILE="$HOME/Documents/UTH/Do_an_data/system_forecast_do_an/final_recording_script/current_state.txt"

current="$(cat "$STATE_FILE" 2>/dev/null)"

if [ "$current" = "media_watching" ]; then
    echo "interactive_light" > "$STATE_FILE"
    notify-send -t 3000 "interactive_light"
else
    echo "media_watching" > "$STATE_FILE"
    notify-send -t 3000 "media_watching"
fi
