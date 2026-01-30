#!/usr/bin/env nu

# Define a command with arguments
def main [
  ...params: string  # variadic arguments
] {
  if ($params | is-empty) {
    error make {
      msg: "You must provide at least one column name"
    }
  }

  loop {
    open comprehensive_activity_log.csv
    | last
    | select ...$params
    | notify-send -t 1000 $"($in)"

    sleep 1sec
  }
}
