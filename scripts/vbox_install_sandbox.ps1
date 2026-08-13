[CmdletBinding()]
param(
    [string]$IsoPath = "",
    [string]$EvidencePrefix = "",
    [ValidateRange(32768, 262144)]
    [int]$DiskSizeMiB = 65536,
    [ValidateRange(4096, 32768)]
    [int]$MemoryMiB = 16384,
    [ValidateRange(2, 32)]
    [int]$Cpus = 16,
    [ValidateRange(3, 120)]
    [int]$ForegroundDelaySeconds = 45,
    [switch]$AdvanceOfflineSetup,
    [switch]$AdvanceCalamaresToPartitions,
    [switch]$SelectDisposableEraseDisk,
    [switch]$InteractiveGui,
    [ValidateRange(0, 900)]
    [int]$InteractionHoldSeconds = 0,
    [switch]$CaptureCalamaresLog,
    [switch]$TestDisposableRecoveryGuardFailClosed,
    [switch]$InventoryDisposableAudio,
    [switch]$TestDisposablePipeWireLoopback,
    [switch]$TestDisposableRecoveryReadback
)

$ErrorActionPreference = "Stop"
if (-not $IsoPath) {
    $IsoPath = Join-Path $PSScriptRoot "..\dist\clausis-0.4.1-amd64.iso"
}
if (-not $EvidencePrefix) {
    $EvidencePrefix = Join-Path $PSScriptRoot "..\dist\clausis-install-sandbox"
}
$vboxManage = Join-Path $env:ProgramFiles "Oracle\VirtualBox\VBoxManage.exe"
$smoke = Join-Path $PSScriptRoot "vbox_acpi_smoke.ps1"
if (-not (Test-Path -LiteralPath $vboxManage -PathType Leaf)) {
    throw "VBoxManage was not found at $vboxManage"
}
if (-not (Test-Path -LiteralPath $smoke -PathType Leaf)) {
    throw "VirtualBox smoke harness was not found at $smoke"
}
if ($AdvanceCalamaresToPartitions -and -not $AdvanceOfflineSetup) {
    throw "Calamares navigation requires -AdvanceOfflineSetup"
}
if ($CaptureCalamaresLog -and -not $AdvanceOfflineSetup) {
    throw "Calamares log capture requires -AdvanceOfflineSetup"
}
if ($TestDisposableRecoveryGuardFailClosed -and
    ($AdvanceCalamaresToPartitions -or $CaptureCalamaresLog)) {
    throw "Recovery guard probe must run separately from Calamares navigation"
}
if ($InventoryDisposableAudio -and
    ($TestDisposableRecoveryGuardFailClosed -or $TestDisposablePipeWireLoopback -or
     $TestDisposableRecoveryReadback -or
     $AdvanceCalamaresToPartitions -or
     $CaptureCalamaresLog)) {
    throw "Audio inventory must run as a separate disposable probe"
}
if ($TestDisposablePipeWireLoopback -and
    ($TestDisposableRecoveryGuardFailClosed -or $TestDisposableRecoveryReadback -or
     $AdvanceCalamaresToPartitions -or
     $CaptureCalamaresLog)) {
    throw "PipeWire loopback must run as a separate disposable probe"
}
if ($TestDisposableRecoveryReadback -and
    ($TestDisposableRecoveryGuardFailClosed -or $TestDisposablePipeWireLoopback -or
     $AdvanceCalamaresToPartitions -or $CaptureCalamaresLog)) {
    throw "Recovery readback must run as a separate disposable probe"
}
if ($SelectDisposableEraseDisk -and -not $AdvanceCalamaresToPartitions) {
    throw "Erase selection requires -AdvanceCalamaresToPartitions"
}
if ($InteractionHoldSeconds -gt 0 -and
    (-not $InteractiveGui -or -not $AdvanceCalamaresToPartitions)) {
    throw "Interaction hold requires GUI navigation to disposable Partitions"
}

$iso = (Resolve-Path -LiteralPath $IsoPath).Path
$expectedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $iso).Hash.ToLowerInvariant()
$distRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\dist"))
$sandboxRoot = [IO.Path]::GetFullPath((Join-Path $distRoot ("clausis-install-sandbox-{0}" -f $PID)))
$requiredPrefix = $distRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
if (-not $sandboxRoot.StartsWith($requiredPrefix, [StringComparison]::OrdinalIgnoreCase) -or
    -not ([IO.Path]::GetFileName($sandboxRoot)).StartsWith(
        "clausis-install-sandbox-", [StringComparison]::Ordinal
    )) {
    throw "Disposable sandbox path escaped the project dist directory"
}

$vmName = "Clausis-Install-Sandbox-$PID"
$vdi = Join-Path $sandboxRoot "$vmName.vdi"
$summaryPath = "$EvidencePrefix-summary.json"
$registered = $false
$smokeResult = $null
$removed = $false

function Invoke-VBox([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments) {
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = @(& $vboxManage @Arguments 2>&1)
        $vboxExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $savedPreference
    }
    if ($vboxExitCode -ne 0) {
        throw "VBoxManage failed: $($Arguments -join ' '): $($output -join ' ')"
    }
    return $output
}

New-Item -ItemType Directory -Path $sandboxRoot | Out-Null
try {
    try {
        & $vboxManage showvminfo $vmName --machinereadable 2>$null | Out-Null
        $existingVmExitCode = $LASTEXITCODE
    } catch {
        $existingVmExitCode = 1
    }
    if ($existingVmExitCode -eq 0) {
        throw "Disposable VM name already exists: $vmName"
    }

    Invoke-VBox createvm --name $vmName --ostype Debian_64 --basefolder $sandboxRoot --register | Out-Null
    $registered = $true
    Invoke-VBox modifyvm $vmName --firmware efi --memory $MemoryMiB --cpus $Cpus `
        --graphicscontroller vmsvga --vram 128 --boot1 dvd --boot2 disk --boot3 none `
        --boot4 none --nic1 nat --uart1 off --audio-enabled on --audio-out on `
        --audio-in $(if ($InventoryDisposableAudio -or $TestDisposablePipeWireLoopback -or
            $TestDisposableRecoveryReadback) {
            "on"
        } else { "off" }) | Out-Null
    Invoke-VBox storagectl $vmName --name SATA --add sata --controller IntelAhci --portcount 1 | Out-Null
    Invoke-VBox storagectl $vmName --name IDE --add ide --controller PIIX4 | Out-Null
    Invoke-VBox createmedium disk --filename $vdi --size $DiskSizeMiB --format VDI --variant Standard | Out-Null
    $resolvedVdi = (Resolve-Path -LiteralPath $vdi).Path
    if (-not $resolvedVdi.StartsWith(
        $sandboxRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Disposable VDI escaped its sandbox directory"
    }
    Invoke-VBox storageattach $vmName --storagectl SATA --port 0 --device 0 `
        --type hdd --medium $resolvedVdi | Out-Null
    Invoke-VBox storageattach $vmName --storagectl IDE --port 0 --device 0 `
        --type dvddrive --medium $iso | Out-Null

    $smokeResult = & $smoke -VmName $vmName -IsoPath $iso -ExpectedVdi $resolvedVdi `
        -EvidencePrefix $EvidencePrefix -CaptureForeground `
        -CompleteOfflineSetupForDisposableInstaller:$AdvanceOfflineSetup `
        -AdvanceCalamaresToPartitions:$AdvanceCalamaresToPartitions `
        -SelectDisposableEraseDisk:$SelectDisposableEraseDisk `
        -InteractiveGui:$InteractiveGui `
        -InteractionHoldSeconds $InteractionHoldSeconds `
        -CaptureCalamaresLog:$CaptureCalamaresLog `
        -TestDisposableRecoveryGuardFailClosed:$TestDisposableRecoveryGuardFailClosed `
        -InventoryDisposableAudio:$InventoryDisposableAudio `
        -TestDisposablePipeWireLoopback:$TestDisposablePipeWireLoopback `
        -TestDisposableRecoveryReadback:$TestDisposableRecoveryReadback `
        -ForegroundDelaySeconds $ForegroundDelaySeconds -BootTimeoutSeconds 180 `
        -DesktopTimeoutSeconds 240 -ShutdownTimeoutSeconds 90
    if (@($smokeResult).Count -ne 1 -or $smokeResult.IsoSha256 -ne $expectedHash -or
        $smokeResult.FinalState -ne "poweroff" -or -not $smokeResult.ForegroundCaptured -or
        $smokeResult.OfflineSetupInputSent -ne [bool]$AdvanceOfflineSetup -or
        ($AdvanceOfflineSetup -and -not $smokeResult.CalamaresReady) -or
        $smokeResult.CalamaresNavigationInputSent -ne [bool]$AdvanceCalamaresToPartitions) {
        throw "Disposable VM did not complete the exact ISO readiness gate"
    }
    if ($smokeResult.DisposableEraseSelectionInputSent -ne [bool]$SelectDisposableEraseDisk) {
        throw "Disposable VM did not complete the exact ISO readiness gate"
    }
    if ($smokeResult.CalamaresLogCaptured -ne [bool]$CaptureCalamaresLog) {
        throw "Disposable VM did not complete the exact ISO readiness gate"
    }
    if ($smokeResult.RecoveryGuardFailClosed -ne
        [bool]$TestDisposableRecoveryGuardFailClosed) {
        throw "Disposable VM did not complete the recovery guard gate"
    }
    if ($TestDisposableRecoveryGuardFailClosed -and
        -not $smokeResult.ForcedDisposableCleanup) {
        throw "Recovery guard probe did not record forced disposable cleanup"
    }
    if ($smokeResult.AudioInventoryPassed -ne [bool]$InventoryDisposableAudio) {
        throw "Disposable VM did not complete the audio inventory gate"
    }
    if ($smokeResult.PipeWireLoopbackPassed -ne [bool]$TestDisposablePipeWireLoopback) {
        throw "Disposable VM did not complete the PipeWire loopback gate"
    }
    if ($smokeResult.RecoveryReadbackAudioPassed -ne
        [bool]$TestDisposableRecoveryReadback) {
        throw "Disposable VM did not complete the Recovery readback gate"
    }
}
finally {
    if ($registered) {
        try {
            $state = (@(& $vboxManage showvminfo $vmName --machinereadable 2>$null) |
                Select-String '^VMState=').ToString()
            if ($state -notmatch '"poweroff"') {
                & $vboxManage controlvm $vmName poweroff 2>$null | Out-Null
            }
        } catch {}
        Invoke-VBox unregistervm $vmName --delete | Out-Null
        $removed = $true
    }
    if (Test-Path -LiteralPath $sandboxRoot -PathType Container) {
        # VBoxSVC can retain VBoxHardening.log for a fraction of a second after
        # unregistervm --delete. Retry only this already validated sandbox path.
        for ($cleanupAttempt = 0; $cleanupAttempt -lt 20 -and
            (Test-Path -LiteralPath $sandboxRoot -PathType Container); $cleanupAttempt++) {
            try {
                Remove-Item -LiteralPath $sandboxRoot -Recurse -Force -ErrorAction Stop
            }
            catch {
                if ($cleanupAttempt -eq 19) { throw }
                Start-Sleep -Milliseconds 250
            }
        }
    }
    [pscustomobject]@{
        VmName = $vmName
        IsoSha256 = $expectedHash
        DisposableVdi = $vdi
        DiskSizeMiB = $DiskSizeMiB
        SmokePassed = $null -ne $smokeResult
        SandboxRemoved = $removed
        Result = $smokeResult
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $summaryPath -Encoding utf8
}

Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
