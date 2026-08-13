[CmdletBinding()]
param(
    [string]$VmName = "Clausis",
    [string]$IsoPath = (Join-Path $PSScriptRoot "..\dist\clausis-0.4.1-amd64.iso"),
    [string]$ExpectedVdi = "G:\VM\Clausis\Clausis.vdi",
    [string]$EvidencePrefix = (Join-Path $PSScriptRoot "..\dist\clausis-acpi-smoke"),
    [switch]$CaptureForeground,
    [switch]$CompleteOfflineSetupForDisposableInstaller,
    [switch]$AdvanceCalamaresToPartitions,
    [switch]$SelectDisposableEraseDisk,
    [switch]$InteractiveGui,
    [ValidateRange(0, 900)]
    [int]$InteractionHoldSeconds = 0,
    [switch]$CaptureCalamaresLog,
    [switch]$TestDisposableRecoveryGuardFailClosed,
    [switch]$InventoryDisposableAudio,
    [switch]$TestDisposablePipeWireLoopback,
    [switch]$TestDisposableRecoveryReadback,
    [ValidateRange(1, 120)]
    [int]$ForegroundDelaySeconds = 3,
    [ValidateRange(15, 180)]
    [int]$SetupTimeoutSeconds = 120,
    [int]$BootTimeoutSeconds = 120,
    [int]$DesktopTimeoutSeconds = 180,
    [int]$ShutdownTimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$vboxManage = Join-Path $env:ProgramFiles "Oracle\VirtualBox\VBoxManage.exe"
if (-not (Test-Path -LiteralPath $vboxManage -PathType Leaf)) {
    throw "VBoxManage was not found at $vboxManage"
}

function Read-MachineInfo {
    # VirtualBox can briefly invalidate the direct-session console object while
    # a VM transitions to poweroff. Retry that bounded host-side read instead
    # of printing a misleading VBOX_E_INVALID_OBJECT_STATE after a clean stop.
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        try {
            $lines = @(& $vboxManage showvminfo $VmName --machinereadable 2>$null)
            $showInfoExitCode = $LASTEXITCODE
        }
        catch {
            $lines = @()
            $showInfoExitCode = 1
        }
        if ($showInfoExitCode -eq 0) {
            $result = @{}
            $lines | ForEach-Object {
                if ($_ -match '^(?<key>"[^"]+"|[^=]+)="?(?<value>.*?[^\"]|)"?$') {
                    $key = $Matches.key.Trim('"')
                    $result[$key] = $Matches.value -replace '\\\\', '\'
                }
            }
            return $result
        }
        Start-Sleep -Milliseconds 200
    }
    throw "VBoxManage could not read machine info for $VmName after 10 attempts"
}

function Wait-ForState([string]$Wanted, [int]$TimeoutSeconds) {
    $timer = [Diagnostics.Stopwatch]::StartNew()
    do {
        Start-Sleep -Milliseconds 500
        $state = (Read-MachineInfo)["VMState"]
    } while ($state -ne $Wanted -and $timer.Elapsed.TotalSeconds -lt $TimeoutSeconds)
    return @{ State = $state; Seconds = $timer.Elapsed.TotalSeconds }
}

function Test-ClausisBranding([string]$Screenshot) {
    $bitmap = [Drawing.Bitmap]::FromFile($Screenshot)
    try {
        $purplePixels = 0
        for ($y = 0; $y -lt $bitmap.Height; $y += 4) {
            for ($x = 0; $x -lt $bitmap.Width; $x += 4) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ($pixel.R -ge 80 -and $pixel.R -le 180 -and
                    $pixel.G -lt 80 -and $pixel.B -ge 150) {
                    $purplePixels++
                    if ($purplePixels -gt 100) { return $true }
                }
            }
        }
        return $false
    }
    finally {
        $bitmap.Dispose()
    }
}

function Test-SetupWindow([string]$Screenshot) {
    $bitmap = [Drawing.Bitmap]::FromFile($Screenshot)
    try {
        $grayPixels = 0
        $left = [math]::Floor($bitmap.Width * 0.18)
        $right = [math]::Floor($bitmap.Width * 0.82)
        $top = [math]::Floor($bitmap.Height * 0.05)
        $bottom = [math]::Floor($bitmap.Height * 0.92)
        for ($y = $top; $y -lt $bottom; $y += 8) {
            for ($x = $left; $x -lt $right; $x += 8) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ($pixel.R -ge 35 -and $pixel.R -le 110 -and
                    [math]::Abs($pixel.R - $pixel.G) -le 12 -and
                    [math]::Abs($pixel.G - $pixel.B) -le 12) {
                    $grayPixels++
                    if ($grayPixels -gt 3000) { return $true }
                }
            }
        }
        return $false
    }
    finally {
        $bitmap.Dispose()
    }
}

function Test-CalamaresWindow([string]$Screenshot) {
    $bitmap = [Drawing.Bitmap]::FromFile($Screenshot)
    try {
        $lightPixels = 0
        $darkPixels = 0
        $sidebarPixels = 0
        $left = [math]::Floor($bitmap.Width * 0.18)
        $right = [math]::Floor($bitmap.Width * 0.95)
        $top = [math]::Floor($bitmap.Height * 0.12)
        $bottom = [math]::Floor($bitmap.Height * 0.92)
        for ($y = $top; $y -lt $bottom; $y += 8) {
            for ($x = $left; $x -lt $right; $x += 8) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ($pixel.R -ge 180 -and $pixel.G -ge 180 -and $pixel.B -ge 180) {
                    $lightPixels++
                    if ($lightPixels -gt 3000) { return $true }
                }
                if ($pixel.R -ge 35 -and $pixel.R -le 70 -and
                    [math]::Abs($pixel.R - $pixel.G) -le 10 -and
                    [math]::Abs($pixel.G - $pixel.B) -le 10) {
                    $darkPixels++
                }
                if ($x -lt 270 -and $pixel.B -gt $pixel.R + 25 -and
                    $pixel.G -gt $pixel.R + 15) {
                    $sidebarPixels++
                }
            }
        }
        return ($darkPixels -gt 3000 -and $sidebarPixels -gt 80)
    }
    finally {
        $bitmap.Dispose()
    }
}

function Test-EraseDiskSelected([string]$Screenshot) {
    $bitmap = [Drawing.Bitmap]::FromFile($Screenshot)
    try {
        # Calamares' light and dark themes use different content margins. In
        # either case the unselected radio center is grayscale and a selected
        # Qt radio contains a coloured indicator. Sample only that center,
        # never the adjacent disk icon or blue navigation background.
        $darkTheme = $bitmap.GetPixel(600, 400).R -lt 100
        $centerX = if ($darkTheme) { 305 } else { 281 }
        $centerY = if ($darkTheme) { 218 } else { 207 }
        for ($y = $centerY - 4; $y -le $centerY + 4; $y++) {
            for ($x = $centerX - 4; $x -le $centerX + 4; $x++) {
                $pixel = $bitmap.GetPixel($x, $y)
                $maximum = [math]::Max($pixel.R, [math]::Max($pixel.G, $pixel.B))
                $minimum = [math]::Min($pixel.R, [math]::Min($pixel.G, $pixel.B))
                if ($maximum - $minimum -gt 20) {
                    return $true
                }
            }
        }
        return $false
    }
    finally {
        $bitmap.Dispose()
    }
}

function Test-CalamaresPartitionsPage([string]$Screenshot) {
    $bitmap = [Drawing.Bitmap]::FromFile($Screenshot)
    try {
        # The selected Partitions navigation row uses Calamares' lighter blue
        # highlight. Sample its interior, away from glyphs and edges.
        $darkTheme = $bitmap.GetPixel(600, 400).R -lt 100
        $partitionsY = if ($darkTheme) { 383 } else { 363 }
        $welcomeY = if ($darkTheme) { 248 } else { 246 }
        $selected = $bitmap.GetPixel(90, $partitionsY)
        $welcome = $bitmap.GetPixel(90, $welcomeY)
        return ($selected.G -gt $welcome.G + 8 -and
            $selected.B -gt $welcome.B + 15)
    }
    finally {
        $bitmap.Dispose()
    }
}

function Test-TtyCommandProducedOutput([string]$Screenshot) {
    $bitmap = [Drawing.Bitmap]::FromFile($Screenshot)
    try {
        $bright = 0
        for ($y = 265; $y -lt [math]::Min(760, $bitmap.Height); $y += 4) {
            for ($x = 0; $x -lt [math]::Min(1100, $bitmap.Width); $x += 4) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ($pixel.R -gt 130 -and $pixel.G -gt 130 -and $pixel.B -gt 130) {
                    $bright++
                    if ($bright -gt 20) { return $true }
                }
            }
        }
        return $false
    }
    finally {
        $bitmap.Dispose()
    }
}

function Test-RecoveryGuardFailClosed([string]$Screenshot) {
    $bitmap = [Drawing.Bitmap]::FromFile($Screenshot)
    try {
        $greenPixels = 0
        $redPixels = 0
        for ($y = 120; $y -lt [math]::Min(700, $bitmap.Height); $y += 4) {
            for ($x = 80; $x -lt [math]::Min(1180, $bitmap.Width); $x += 4) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ($pixel.G -gt 90 -and $pixel.G -gt $pixel.R * 1.5 -and
                    $pixel.G -gt $pixel.B * 1.5) { $greenPixels++ }
                if ($pixel.R -gt 90 -and $pixel.R -gt $pixel.G * 1.5 -and
                    $pixel.R -gt $pixel.B * 1.5) { $redPixels++ }
            }
        }
        return ($greenPixels -gt 10000 -and $redPixels -lt 1000)
    }
    finally {
        $bitmap.Dispose()
    }
}

function Test-AudioInventoryPassed([string]$Screenshot) {
    $bitmap = [Drawing.Bitmap]::FromFile($Screenshot)
    try {
        $greenPixels = 0
        for ($y = 80; $y -lt [math]::Min(720, $bitmap.Height); $y += 4) {
            for ($x = 40; $x -lt [math]::Min(1240, $bitmap.Width); $x += 4) {
                $pixel = $bitmap.GetPixel($x, $y)
                if ($pixel.G -gt 90 -and $pixel.G -gt $pixel.R * 1.5 -and
                    $pixel.G -gt $pixel.B * 1.5) { $greenPixels++ }
            }
        }
        # The inventory deliberately preserves the device listing. Only its
        # single final verdict line has a coloured background.
        return $greenPixels -gt 100
    }
    finally { $bitmap.Dispose() }
}

function Test-PipeWireLoopbackPassed([string]$Screenshot) {
    return Test-AudioInventoryPassed $Screenshot
}

$iso = (Resolve-Path -LiteralPath $IsoPath).Path
$vdi = (Resolve-Path -LiteralPath $ExpectedVdi).Path
if ($CompleteOfflineSetupForDisposableInstaller -and $vdi -notmatch
    '(?i)[\\/]clausis-install-sandbox-\d+[\\/]Clausis-Install-Sandbox-\d+\.vdi$') {
    throw "Offline setup automation is restricted to a disposable installer VDI"
}
if ($AdvanceCalamaresToPartitions -and -not $CompleteOfflineSetupForDisposableInstaller) {
    throw "Calamares navigation requires disposable offline setup completion"
}
if ($CaptureCalamaresLog -and -not $CompleteOfflineSetupForDisposableInstaller) {
    throw "Calamares log capture requires disposable offline setup completion"
}
if ($CaptureCalamaresLog -and $AdvanceCalamaresToPartitions) {
    throw "Calamares log capture and navigation must run separately"
}
if ($TestDisposableRecoveryGuardFailClosed -and
    ($AdvanceCalamaresToPartitions -or $CaptureCalamaresLog)) {
    throw "Recovery guard probe must run separately from Calamares navigation"
}
if ($TestDisposableRecoveryGuardFailClosed -and $vdi -notmatch
    '(?i)[\\/]clausis-install-sandbox-\d+[\\/]Clausis-Install-Sandbox-\d+\.vdi$') {
    throw "Recovery guard probe is restricted to a disposable installer VDI"
}
if ($InventoryDisposableAudio -and $vdi -notmatch
    '(?i)[\\/]clausis-install-sandbox-\d+[\\/]Clausis-Install-Sandbox-\d+\.vdi$') {
    throw "Audio inventory is restricted to a disposable installer VDI"
}
if ($InventoryDisposableAudio -and
    ($TestDisposableRecoveryGuardFailClosed -or $TestDisposablePipeWireLoopback -or
     $TestDisposableRecoveryReadback -or
     $AdvanceCalamaresToPartitions -or
     $CaptureCalamaresLog)) {
    throw "Audio inventory must run as a separate disposable probe"
}
if ($TestDisposablePipeWireLoopback -and $vdi -notmatch
    '(?i)[\\/]clausis-install-sandbox-\d+[\\/]Clausis-Install-Sandbox-\d+\.vdi$') {
    throw "PipeWire loopback is restricted to a disposable installer VDI"
}
if ($TestDisposablePipeWireLoopback -and
    ($TestDisposableRecoveryGuardFailClosed -or $TestDisposableRecoveryReadback -or
     $AdvanceCalamaresToPartitions -or
     $CaptureCalamaresLog)) {
    throw "PipeWire loopback must run as a separate disposable probe"
}
if ($TestDisposableRecoveryReadback -and $vdi -notmatch
    '(?i)[\\/]clausis-install-sandbox-\d+[\\/]Clausis-Install-Sandbox-\d+\.vdi$') {
    throw "Recovery readback is restricted to a disposable installer VDI"
}
if ($TestDisposableRecoveryReadback -and
    ($TestDisposableRecoveryGuardFailClosed -or $TestDisposablePipeWireLoopback -or
     $AdvanceCalamaresToPartitions -or $CaptureCalamaresLog)) {
    throw "Recovery readback must run as a separate disposable probe"
}
if ($SelectDisposableEraseDisk -and -not $AdvanceCalamaresToPartitions) {
    throw "Erase selection requires navigation to disposable Partitions"
}
if ($InteractionHoldSeconds -gt 0 -and
    (-not $InteractiveGui -or -not $AdvanceCalamaresToPartitions)) {
    throw "Interaction hold requires GUI navigation to disposable Partitions"
}
$info = Read-MachineInfo
if ($info.VMState -ne "poweroff") { throw "$VmName must be powered off, got $($info.VMState)" }
if ($info["IDE-0-0"] -ne $iso) { throw "Unexpected ISO mapping: $($info['IDE-0-0'])" }
if ($info["SATA-0-0"] -ne $vdi) { throw "Unexpected VDI mapping: $($info['SATA-0-0'])" }
if ($info.uart1 -ne "off") { throw "UART must be off for the release smoke test" }

$log = Join-Path $info.LogFldr "VBox.log"
$started = $false
try {
    $vmType = if ($InteractiveGui) { "gui" } else { "headless" }
    & $vboxManage startvm $VmName --type $vmType | Out-Null
    $started = $true

    $boot = [Diagnostics.Stopwatch]::StartNew()
    do {
        Start-Sleep -Seconds 2
        $grubMode = (Get-Content -LiteralPath $log -Tail 120) -match 'w=800 h=600'
        if ($grubMode) {
            & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-grub.png"
            $grubReady = Test-ClausisBranding "$EvidencePrefix-grub.png"
        }
    } while (-not $grubReady -and $boot.Elapsed.TotalSeconds -lt $BootTimeoutSeconds)
    if (-not $grubReady) { throw "GRUB readiness was not observed" }

    & $vboxManage controlvm $VmName keyboardputscancode 1c 9c

    $desktop = [Diagnostics.Stopwatch]::StartNew()
    do {
        Start-Sleep -Seconds 3
        $mode = (& $vboxManage showvminfo $VmName | Select-String '^Video mode:').ToString()
        if ($mode -match '1280x(768|800)') {
            & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-live.png"
            # Do not mistake the Debian hand-off background for the finished
            # session merely because the final video mode is already set.
            $desktopReady = Test-ClausisBranding "$EvidencePrefix-live.png"
        }
    } while (-not $desktopReady -and $desktop.Elapsed.TotalSeconds -lt $DesktopTimeoutSeconds)
    if (-not $desktopReady) { throw "Live desktop readiness was not observed: $mode" }

    if ($CaptureForeground) {
        # Escape only closes GNOME's overview. It does not select, activate or
        # advance any setup/installer control.
        & $vboxManage controlvm $VmName keyboardputscancode 01 81
        Start-Sleep -Seconds $ForegroundDelaySeconds
        & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-foreground.png"
    }

    $recoveryGuardFailClosed = $false
    if ($TestDisposableRecoveryGuardFailClosed) {
        # The guard never partitions. Green is emitted only when it rejects,
        # removes its staged key, leaves no partition table, and the first
        # four MiB of the disposable target remain byte-for-byte unchanged.
        & $vboxManage controlvm $VmName keyboardputscancode 1d 38 3d bd b8 9d
        # TTY3 auto-login prints its banner asynchronously. Wait for the shell
        # prompt, then cancel any partial line before injecting the probe.
        Start-Sleep -Seconds 12
        & $vboxManage controlvm $VmName keyboardputscancode 1d 2e ae 9d
        Start-Sleep -Seconds 1
        $probe = 'before=$(sudo dd if=/dev/sda bs=1M count=4 status=none|sha256sum|cut -c1-64); ' +
            'out=$(sudo /usr/libexec/calamares-clausis/calamares_clausis.py ' +
            '--guard-transaction --device /dev/sda --install-mode erase ' +
            '--encrypted true --filesystem btrfs 2>&1); rc=$?; ' +
            'after=$(sudo dd if=/dev/sda bs=1M count=4 status=none|sha256sum|cut -c1-64); ' +
            'if [ $rc -ne 0 ] && [ ! -e /run/clausis-installer/recovery.key ] && ' +
            '! sudo sfdisk -d /dev/sda >/dev/null 2>&1 && [ $before = $after ] && ' +
            'echo $out|grep -q denied; then ' +
            'tput setab 2;tput setaf 0;clear;yes RECOVERY_GUARD_FAIL_CLOSED_OK|head -n 200; ' +
            'else tput setab 1;tput setaf 7;clear;yes RECOVERY_GUARD_FAILURE|head -n 200; fi'
        & $vboxManage controlvm $VmName keyboardputstring $probe
        # keyboardputstring returns before the guest has necessarily drained
        # a long injected line. Do not race Enter against its final bytes.
        Start-Sleep -Seconds 3
        & $vboxManage controlvm $VmName keyboardputscancode 1c 9c
        # The speaker fails closed after its single 120-second backend bound;
        # allow margin for guest scheduling and postcondition checks.
        Start-Sleep -Seconds 180
        & $vboxManage controlvm $VmName screenshotpng `
            "$EvidencePrefix-recovery-guard-fail-closed.png"
        $recoveryGuardFailClosed = Test-RecoveryGuardFailClosed `
            "$EvidencePrefix-recovery-guard-fail-closed.png"
        if (-not $recoveryGuardFailClosed) {
            throw "Recovery guard did not prove a fail-closed, write-free result"
        }
    }

    $audioInventoryPassed = $false
    if ($InventoryDisposableAudio) {
        & $vboxManage controlvm $VmName keyboardputscancode 1d 38 3d bd b8 9d
        Start-Sleep -Seconds 12
        & $vboxManage controlvm $VmName keyboardputscancode 1d 2e ae 9d
        Start-Sleep -Seconds 1
        $probe = 'status=$(wpctl status 2>/dev/null); echo "$status"; ' +
            'echo ---AUDIO-TOOLS---; for c in pw-record pw-play pw-loopback arecord pactl; do ' +
            'printf "%s=" "$c"; command -v "$c" || echo missing; done; ' +
            'if command -v wpctl >/dev/null && echo "$status"|grep -q Sources: && ' +
            'echo "$status"|grep -q Built-in.*Audio; then ' +
            'tput setab 2;tput setaf 0; echo AUDIO_INVENTORY_OK; ' +
            'else tput setab 1;tput setaf 7; echo AUDIO_INVENTORY_FAILURE; fi'
        & $vboxManage controlvm $VmName keyboardputstring $probe
        Start-Sleep -Seconds 3
        & $vboxManage controlvm $VmName keyboardputscancode 1c 9c
        Start-Sleep -Seconds 15
        & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-audio-inventory.png"
        $audioInventoryPassed = Test-AudioInventoryPassed "$EvidencePrefix-audio-inventory.png"
        if (-not $audioInventoryPassed) {
            throw "Guest audio inventory did not expose a PipeWire/PulseAudio source"
        }
    }

    $pipeWireLoopbackPassed = $false
    if ($TestDisposablePipeWireLoopback) {
        & $vboxManage controlvm $VmName keyboardputscancode 1d 38 3d bd b8 9d
        Start-Sleep -Seconds 12
        & $vboxManage controlvm $VmName keyboardputscancode 1d 2e ae 9d
        Start-Sleep -Seconds 1
        $probe = @'
set -u
rm -f /tmp/clausis-loop.wav /tmp/clausis-loop.log
pw-loopback --delay=2 --capture-props='{"stream.capture.sink":true}' --playback-props='{"media.class":"Audio/Source","node.name":"clausis-delayed","node.description":"Clausis Delayed Source"}' >/tmp/clausis-loop.log 2>&1 &
loop_pid=$!
sleep 4
source_id=$(wpctl status | sed -n 's/.* \([0-9][0-9]*\)\. clausis-delayed.*/\1/p' | head -n1)
if [ -n "$source_id" ]; then wpctl set-default "$source_id"; fi
timeout 12 pw-record --target="$source_id" --rate=16000 --channels=1 --format=s16 /tmp/clausis-loop.wav >/dev/null 2>&1 &
record_pid=$!
sleep 1
spd-say -w -l de 'Clausis Audiotest. Die Zahlen lauten: sieben, zwei, neun. Ich wiederhole: sieben, zwei, neun.'
wait "$record_pid" || true
kill "$loop_pid" 2>/dev/null || true
audio_ok=false
if [ -n "$source_id" ] && python3 - /tmp/clausis-loop.wav <<'PY'
import sys, wave
with wave.open(sys.argv[1], 'rb') as stream:
    frames = stream.readframes(stream.getnframes())
raise SystemExit(0 if len(frames) > 16000 and len(set(frames)) > 8 else 1)
PY
then audio_ok=true; fi
transcript=$(timeout 90 /opt/clausis/bin/python - /tmp/clausis-loop.wav <<'PY'
import sys
from pathlib import Path
from clausis.speech import LocalWhisper
print(LocalWhisper('/usr/share/clausis/models/faster-whisper-base', language='de').transcribe(Path(sys.argv[1])))
PY
) || transcript=
echo "TRANSCRIPT: $transcript"
normalized=$(printf '%s' "$transcript" | tr '[:upper:]' '[:lower:]')
if $audio_ok && printf '%s' "$normalized" | grep -Eq '(sieben|7)' &&
   printf '%s' "$normalized" | grep -Eq '(zwei|2)' &&
   printf '%s' "$normalized" | grep -Eq '(neun|9)'; then
    tput setab 2; tput setaf 0; echo PIPEWIRE_LOOPBACK_OK
else
    wpctl status; cat /tmp/clausis-loop.log
    tput setab 1; tput setaf 7; echo PIPEWIRE_LOOPBACK_FAILURE
fi
'@
        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($probe))
        & $vboxManage controlvm $VmName keyboardputstring "echo $encoded|base64 -d|bash"
        # This encoded probe is several thousand keystrokes. VBoxManage can
        # return while the guest keyboard queue is still draining.
        Start-Sleep -Seconds 12
        & $vboxManage controlvm $VmName keyboardputscancode 1c 9c
        Start-Sleep -Seconds 120
        & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-pipewire-loopback.png"
        $pipeWireLoopbackPassed = Test-PipeWireLoopbackPassed `
            "$EvidencePrefix-pipewire-loopback.png"
        if (-not $pipeWireLoopbackPassed) {
            throw "PipeWire/local-STT probe did not recognize delayed speech output"
        }
    }

    $recoveryReadbackAudioPassed = $false
    if ($TestDisposableRecoveryReadback) {
        & $vboxManage controlvm $VmName keyboardputscancode 1d 38 3d bd b8 9d
        Start-Sleep -Seconds 12
        & $vboxManage controlvm $VmName keyboardputscancode 1d 2e ae 9d
        Start-Sleep -Seconds 1
        $probe = @'
set -u
rm -f /tmp/clausis-recovery-readback.wav
timeout 360 /opt/clausis/bin/python - <<'PY'
import os
from pathlib import Path
import subprocess
import time

from clausis.installer import generate_recovery_key
from clausis.speech import LocalWhisper, SpeechError, SystemSpeaker
from clausis.trusted_audio import (
    _RECOVERY_TRANSCRIPTION_PROMPT,
    format_recovery_key_for_speech,
    normalize_spoken_recovery_key,
)

key = generate_recovery_key()
loop = subprocess.Popen([
    'pw-loopback', '--delay=2',
    '--capture-props={"stream.capture.sink":true}',
    '--playback-props={"media.class":"Audio/Source","node.name":"clausis-recovery-readback","node.description":"Clausis Recovery Readback"}',
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
recorder = None
try:
    time.sleep(4)
    status = subprocess.run(['wpctl', 'status'], check=True, capture_output=True, text=True).stdout
    source_id = next(
        line.split('.')[0].strip(' *│├─')
        for line in status.splitlines() if '. clausis-recovery-readback' in line
    )
    subprocess.run(['wpctl', 'set-default', source_id], check=True)
    spoken_key = format_recovery_key_for_speech(key)
    SystemSpeaker().speak(
        'Notieren Sie jetzt den einmaligen LUKS Recovery Schlüssel. '
        'Er wird nach dieser Installation nicht erneut angezeigt. '
        'Der Schlüssel folgt jetzt.',
        language='de',
    )
    SystemSpeaker().speak(spoken_key, language='de')
    SystemSpeaker().speak('Ich wiederhole den Recovery Schlüssel jetzt.', language='de')
    SystemSpeaker().speak(spoken_key, language='de')

    # Simulate only the user's handwritten-note readback through real audio.
    # The production prompt above is deliberately not part of microphone input.
    recorder = subprocess.Popen([
        'pw-record', f'--target={source_id}', '--rate=16000', '--channels=1',
        '--format=s16', '/tmp/clausis-recovery-readback.wav',
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        SystemSpeaker().speak(spoken_key, language='de')
    except Exception:
        recorder.terminate()
        raise SystemExit(4)
    time.sleep(3)
    recorder.terminate()
    recorder.wait(timeout=15)
    recorder = None
    transcript = LocalWhisper(
        '/usr/share/clausis/models/faster-whisper-base',
        language='de',
        initial_prompt=_RECOVERY_TRANSCRIPTION_PROMPT,
    ).transcribe(Path('/tmp/clausis-recovery-readback.wav'))
    try:
        normalized = normalize_spoken_recovery_key(transcript)
    except SpeechError:
        raise SystemExit(3)
    if normalized != key:
        raise SystemExit(2)
finally:
    if recorder is not None:
        recorder.terminate()
    loop.terminate()
    try:
        loop.wait(timeout=5)
    except subprocess.TimeoutExpired:
        loop.kill()
    try:
        os.unlink('/tmp/clausis-recovery-readback.wav')
    except FileNotFoundError:
        pass
PY
rc=$?
if [ "$rc" -eq 0 ] && [ ! -e /tmp/clausis-recovery-readback.wav ]; then
    tput setab 2; tput setaf 0; clear; yes RECOVERY_READBACK_AUDIO_OK | head -n 200
else
    rm -f /tmp/clausis-recovery-readback.wav
    case "$rc" in
        2) verdict=RECOVERY_READBACK_COMPARE_FAILURE ;;
        3) verdict=RECOVERY_READBACK_NORMALIZE_FAILURE ;;
        4) verdict=RECOVERY_READBACK_SPEAKER_FAILURE ;;
        124) verdict=RECOVERY_READBACK_TIMEOUT ;;
        *) verdict=RECOVERY_READBACK_RUNTIME_FAILURE ;;
    esac
    tput setab 1; tput setaf 7; clear; tput cup 20 20; echo "$verdict"
fi
'@
        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($probe))
        & $vboxManage controlvm $VmName keyboardputstring "echo $encoded|base64 -d|bash"
        Start-Sleep -Seconds 15
        & $vboxManage controlvm $VmName keyboardputscancode 1c 9c
        Start-Sleep -Seconds 375
        & $vboxManage controlvm $VmName screenshotpng `
            "$EvidencePrefix-recovery-readback-audio.png"
        $recoveryReadbackAudioPassed = Test-PipeWireLoopbackPassed `
            "$EvidencePrefix-recovery-readback-audio.png"
        if (-not $recoveryReadbackAudioPassed) {
            throw "Full Recovery-key speech did not survive local audio readback"
        }
    }

    if ($CompleteOfflineSetupForDisposableInstaller) {
        if (-not $CaptureForeground) {
            throw "Disposable offline setup requires a foreground capture first"
        }
        # Desktop readiness can precede the spoken welcome and setup window by
        # more than the foreground delay. Never send setup input until the
        # large neutral GTK surface is visibly present.
        $setupWait = [Diagnostics.Stopwatch]::StartNew()
        $setupReady = Test-SetupWindow "$EvidencePrefix-foreground.png"
        while (-not $setupReady -and $setupWait.Elapsed.TotalSeconds -lt $SetupTimeoutSeconds) {
            Start-Sleep -Seconds 3
            & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-foreground.png"
            $setupReady = Test-SetupWindow "$EvidencePrefix-foreground.png"
        }
        if (-not $setupReady) { throw "Clausis setup window readiness was not observed" }

        # Use GTK mnemonics rather than coordinates. The fixed PIN exists only
        # inside this disposable VM and the VM/VDI are deleted by its caller.
        & $vboxManage controlvm $VmName keyboardputscancode 38 19 99 b8
        & $vboxManage controlvm $VmName keyboardputscancode 03 83 05 85 07 87 09 89 02 82 0b 8b
        & $vboxManage controlvm $VmName keyboardputscancode 38 11 91 b8
        & $vboxManage controlvm $VmName keyboardputscancode 03 83 05 85 07 87 09 89 02 82 0b 8b
        # GTK did not activate the save button through its Alt+S mnemonic in
        # the real VM. From the repeat-PIN field the declared focus order is
        # voice button, then save button. Capture that focused state before
        # pressing Enter so the transition has reviewable evidence.
        & $vboxManage controlvm $VmName keyboardputscancode 0f 8f 0f 8f
        Start-Sleep -Seconds 1
        & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-before-save.png"
        & $vboxManage controlvm $VmName keyboardputscancode 1c 9c
        $transitionWait = [Diagnostics.Stopwatch]::StartNew()
        $setupClosed = $false
        $calamaresReady = $false
        while (-not $calamaresReady -and
            $transitionWait.Elapsed.TotalSeconds -lt $SetupTimeoutSeconds) {
            Start-Sleep -Seconds 3
            & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-after-setup.png"
            $setupSurfaceVisible = Test-SetupWindow "$EvidencePrefix-after-setup.png"
            if (-not $setupSurfaceVisible) {
                $setupClosed = $true
            }
            if ($setupClosed -and
                (Test-CalamaresWindow "$EvidencePrefix-after-setup.png")) {
                # The original setup surface disappeared first. Calamares has
                # a separately detected large light content surface.
                $calamaresReady = $true
            }
        }
        if (-not $setupClosed) { throw "Clausis setup window did not close after save activation" }
        if (-not $calamaresReady) { throw "Calamares window readiness was not observed" }

        if ($CaptureCalamaresLog) {
            # Diagnostic-only TTY in the disposable live VM. The credentials
            # are for the documented ephemeral live account. Display the
            # existing log; do not mutate disk state.
            Start-Sleep -Seconds 60
            & $vboxManage controlvm $VmName keyboardputscancode 1d 38 3d bd b8 9d
            Start-Sleep -Seconds 3
            & $vboxManage controlvm $VmName keyboardputstring `
                "sudo tail -120 /root/.cache/calamares/session.log"
            & $vboxManage controlvm $VmName keyboardputscancode 1c 9c
            Start-Sleep -Seconds 3
            & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-calamares-log.png"
            if (-not (Test-TtyCommandProducedOutput `
                "$EvidencePrefix-calamares-log.png")) {
                throw "Calamares log command produced no visible TTY output"
            }
        }

        if ($AdvanceCalamaresToPartitions) {
            # The welcome page can be visible while Calamares still reports
            # "Waiting for 1 module(s)" and Next is disabled. Give hardware
            # discovery a bounded settling interval. Once requirements are
            # complete and English is active, Qt's Alt+N mnemonic uniquely
            # activates Next on Welcome, Location and Keyboard. Stop before
            # touching any control on Partitions.
            Start-Sleep -Seconds 30
            & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-calamares-welcome-ready.png"
            foreach ($page in @("location", "keyboard", "partitions")) {
                & $vboxManage controlvm $VmName keyboardputscancode 38 31 b1 b8
                Start-Sleep -Seconds 15
                & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-calamares-$page.png"
            }
            if (-not (Test-CalamaresPartitionsPage `
                "$EvidencePrefix-calamares-partitions.png")) {
                throw "Calamares Partitions page was not visually observed"
            }
            if ($InteractionHoldSeconds -gt 0) {
                Start-Sleep -Seconds $InteractionHoldSeconds
                & $vboxManage controlvm $VmName screenshotpng `
                    "$EvidencePrefix-calamares-after-interaction.png"
            }
            if ($SelectDisposableEraseDisk) {
                # Select the exact, uniquely named radio through the same
                # guest AT-SPI API used by Clausis voice control. Run the
                # command on the disposable live TTY, then return to GNOME.
                # This changes only UI state and never activates Next.
                & $vboxManage controlvm $VmName keyboardputscancode 1d 38 3d bd b8 9d
                Start-Sleep -Seconds 3
                $pythonSource = "from clausis.gnome_adapter import PyAtSpiDesktop`n" + `
                    "desktop=PyAtSpiDesktop()`n" + `
                    "print(desktop.context())`n" + `
                    "print(desktop.select_named_radio('Erase disk'))`n"
                $pythonBase64 = [Convert]::ToBase64String(
                    [Text.Encoding]::UTF8.GetBytes($pythonSource)
                )
                $atspiCommand = "(sleep 5;echo $pythonBase64|base64 -d|env " + `
                    "DISPLAY=:0 XAUTHORITY=`$(find /run/user/1000 -maxdepth 1 " + `
                    "-name .mutter-Xwaylandauth.* -print -quit) " + `
                    "XDG_RUNTIME_DIR=/run/user/1000 " + `
                    "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus " + `
                    "python3)>/tmp/clausis-atspi-erase.log 2>&1 &"
                & $vboxManage controlvm $VmName keyboardputstring $atspiCommand
                & $vboxManage controlvm $VmName keyboardputscancode 1c 9c
                Start-Sleep -Seconds 1
                & $vboxManage controlvm $VmName keyboardputscancode 1d 38 3c bc b8 9d
                Start-Sleep -Seconds 12
                & $vboxManage controlvm $VmName screenshotpng `
                    "$EvidencePrefix-calamares-erase-selected.png"
                if (-not (Test-EraseDiskSelected `
                    "$EvidencePrefix-calamares-erase-selected.png")) {
                    & $vboxManage controlvm $VmName keyboardputscancode `
                        1d 38 3d bd b8 9d
                    Start-Sleep -Seconds 2
                    & $vboxManage controlvm $VmName keyboardputstring `
                        "tail -40 /tmp/clausis-atspi-erase.log"
                    & $vboxManage controlvm $VmName keyboardputscancode 1c 9c
                    Start-Sleep -Seconds 2
                    & $vboxManage controlvm $VmName screenshotpng `
                        "$EvidencePrefix-calamares-erase-atspi-error.png"
                    throw "Disposable Erase disk selection was not visually observed"
                }
            }
        }
    }

    $shutdown = [Diagnostics.Stopwatch]::StartNew()
    $forcedDisposableCleanup = $false
    if (($TestDisposableRecoveryGuardFailClosed -and $recoveryGuardFailClosed) -or
        ($InventoryDisposableAudio -and $audioInventoryPassed) -or
        ($TestDisposablePipeWireLoopback -and $pipeWireLoopbackPassed) -or
        ($TestDisposableRecoveryReadback -and $recoveryReadbackAudioPassed)) {
        # This probe already proved its guest predicates. Keep its cleanup
        # independent from the separate ACPI release gate and record the
        # forced host-side stop explicitly.
        & $vboxManage controlvm $VmName poweroff | Out-Null
        $result = Wait-ForState -Wanted "poweroff" -TimeoutSeconds 30
        $forcedDisposableCleanup = $true
    }
    else {
        & $vboxManage controlvm $VmName acpipowerbutton
        $result = Wait-ForState -Wanted "poweroff" -TimeoutSeconds $ShutdownTimeoutSeconds
        if ($result.State -ne "poweroff") {
            & $vboxManage controlvm $VmName screenshotpng "$EvidencePrefix-timeout.png"
            throw ("One ACPI request did not reach poweroff within {0:N1} seconds" -f $result.Seconds)
        }
    }
    if ($result.State -ne "poweroff") {
        throw "Disposable recovery-guard cleanup did not reach poweroff"
    }
    $started = $false

    [pscustomobject]@{
        VmName = $VmName
        IsoSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $iso).Hash.ToLowerInvariant()
        GrubReadySeconds = [math]::Round($boot.Elapsed.TotalSeconds, 1)
        DesktopReadySeconds = [math]::Round($desktop.Elapsed.TotalSeconds, 1)
        ForegroundCaptured = [bool]$CaptureForeground
        ForegroundDelaySeconds = if ($CaptureForeground) { $ForegroundDelaySeconds } else { 0 }
        SetupReadySeconds = if ($CompleteOfflineSetupForDisposableInstaller) {
            [math]::Round($setupWait.Elapsed.TotalSeconds, 1)
        } else { 0 }
        OfflineSetupInputSent = [bool]$CompleteOfflineSetupForDisposableInstaller
        CalamaresReady = if ($CompleteOfflineSetupForDisposableInstaller) {
            [bool]$calamaresReady
        } else { $false }
        CalamaresNavigationInputSent = [bool]$AdvanceCalamaresToPartitions
        DisposableEraseSelectionInputSent = [bool]$SelectDisposableEraseDisk
        CalamaresLogCaptured = [bool]$CaptureCalamaresLog
        RecoveryGuardFailClosed = [bool]$recoveryGuardFailClosed
        AudioInventoryPassed = [bool]$audioInventoryPassed
        PipeWireLoopbackPassed = [bool]$pipeWireLoopbackPassed
        RecoveryReadbackAudioPassed = [bool]$recoveryReadbackAudioPassed
        ForcedDisposableCleanup = [bool]$forcedDisposableCleanup
        PoweroffSeconds = [math]::Round($result.Seconds, 1)
        FinalState = $result.State
    }
}
finally {
    if ($started) {
        $state = (Read-MachineInfo)["VMState"]
        if ($state -eq "running") {
            & $vboxManage controlvm $VmName poweroff | Out-Null
        }
    }
}
