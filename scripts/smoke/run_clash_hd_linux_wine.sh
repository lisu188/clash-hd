#!/usr/bin/env bash
# Launch one HD candidate under wine on a headless Xvfb display and drive a real
# DirectInput mouse route with xdotool, capturing frames.
#
# This is the per-target worker invoked by tools/run_hd_linux_validation.py. It
# mirrors the -AllowVisibleRuntime guard of the Windows harnesses: it refuses to
# launch unless --allow-visible-runtime is passed (which the driver only adds
# after explicit user approval).
#
# It does NOT patch the binary or prepare fixtures -- the Python driver does that
# and passes an already-built candidate path (a wine C:\ path). It writes a
# per-target summary JSON the driver folds into the run manifest.
set -euo pipefail

wine_prefix=""
display=":99"
candidate=""
route=""
route_points=""
followup_points=""
out_dir=""
click_hold_ms=300
click_repeat=2
allow_visible_runtime=0
screen_size="1024x768"

die() { echo "error: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wine-prefix) wine_prefix="$2"; shift 2 ;;
    --display) display="$2"; shift 2 ;;
    --candidate) candidate="$2"; shift 2 ;;
    --route) route="$2"; shift 2 ;;
    --route-points) route_points="$2"; shift 2 ;;
    --followup-points) followup_points="$2"; shift 2 ;;
    --out-dir) out_dir="$2"; shift 2 ;;
    --click-hold-ms) click_hold_ms="$2"; shift 2 ;;
    --click-repeat) click_repeat="$2"; shift 2 ;;
    --screen-size) screen_size="$2"; shift 2 ;;
    --allow-visible-runtime) allow_visible_runtime=1; shift ;;
    *) die "unknown argument: $1" ;;
  esac
done

if [[ "$allow_visible_runtime" -ne 1 ]]; then
  die "this worker launches a visible wine runtime; pass --allow-visible-runtime only after explicit user approval"
fi
[[ -n "$wine_prefix" ]] || die "--wine-prefix is required"
[[ -n "$candidate" ]] || die "--candidate is required"
[[ -n "$out_dir" ]] || die "--out-dir is required"
command -v wine >/dev/null 2>&1 || die "wine is not installed (see the runbook's apt-get install line)"
command -v xdotool >/dev/null 2>&1 || die "xdotool is not installed"

mkdir -p "$out_dir"
export WINEPREFIX="$wine_prefix"
export WINEDEBUG="${WINEDEBUG:-fixme-all}"
export DISPLAY="$display"

# Ensure an Xvfb display is up; start a private one if not.
started_xvfb=0
if ! xdpyinfo -display "$display" >/dev/null 2>&1; then
  command -v Xvfb >/dev/null 2>&1 || die "Xvfb is not installed and $display is not running"
  Xvfb "$display" -screen 0 "${screen_size}x24" >/dev/null 2>&1 &
  xvfb_pid=$!
  started_xvfb=1
  for _ in $(seq 1 30); do
    xdpyinfo -display "$display" >/dev/null 2>&1 && break
    sleep 0.2
  done
fi

cleanup() {
  wineserver -k >/dev/null 2>&1 || true
  if [[ "$started_xvfb" -eq 1 && -n "${xvfb_pid:-}" ]]; then
    kill "$xvfb_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

capture_frame() {
  local target="$1"
  if command -v ffmpeg >/dev/null 2>&1; then
    ffmpeg -y -loglevel error -f x11grab -video_size "$screen_size" -i "$display" -frames:v 1 "$target" >/dev/null 2>&1 || true
  elif command -v import >/dev/null 2>&1; then
    import -display "$display" -window root "$target" >/dev/null 2>&1 || true
  fi
}

drive_points() {
  # semicolon-separated points, each "x,y" or "name:x,y" (the run-plan specs
  # name their aim points); held left-click at each.
  local points="$1"
  local hold_s
  hold_s=$(awk "BEGIN { printf \"%.3f\", $click_hold_ms/1000 }")
  IFS=';' read -ra parts <<< "$points"
  for p in "${parts[@]}"; do
    [[ -z "$p" ]] && continue
    p="${p##*:}"
    local x="${p%,*}" y="${p#*,}"
    for _ in $(seq 1 "$click_repeat"); do
      xdotool mousemove --sync "$x" "$y" >/dev/null 2>&1 || true
      xdotool mousedown 1 >/dev/null 2>&1 || true
      sleep "$hold_s"
      xdotool mouseup 1 >/dev/null 2>&1 || true
      sleep 0.15
    done
  done
}

launch_log="$out_dir/wine-launch.log"
echo "launching candidate: $candidate (route=$route)" | tee "$launch_log"

# Launch the candidate; give it time to reach the menu.
wine "$candidate" >>"$launch_log" 2>&1 &
game_pid=$!
sleep "${POST_LAUNCH_WAIT_SEC:-8}"

capture_frame "$out_dir/before.png"
[[ -n "$route_points" ]] && drive_points "$route_points"
sleep 2
capture_frame "$out_dir/after-route.png"
[[ -n "$followup_points" ]] && drive_points "$followup_points"
sleep 2
capture_frame "$out_dir/after-followup.png"

# Did the process stay alive through the route (no crash)?
no_crash=false
if kill -0 "$game_pid" >/dev/null 2>&1; then
  no_crash=true
fi
kill "$game_pid" >/dev/null 2>&1 || true

# Escape backslashes and double quotes so Windows-style candidate paths
# (C:\ClashTests\...) produce valid JSON strings.
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "$s"
}

cat > "$out_dir/target-summary.json" <<JSON
{
  "candidate": "$(json_escape "$candidate")",
  "route": "$(json_escape "$route")",
  "route_points": "$(json_escape "$route_points")",
  "followup_points": "$(json_escape "$followup_points")",
  "no_crash": $no_crash,
  "artifacts": ["before.png", "after-route.png", "after-followup.png", "wine-launch.log"],
  "note": "operator must review the captured frames and fill observed_result / evidence / pass_fail_notes before assembling the proof"
}
JSON

echo "wrote $out_dir/target-summary.json (no_crash=$no_crash)"
