[CmdletBinding()]
param(
    [string]$VmName = "Clausis",
    [string]$IsoPath = (Join-Path $PSScriptRoot "..\dist\clausis-0.4.1-amd64.iso"),
    [string]$ExpectedVdi = "G:\VM\Clausis\Clausis.vdi",
    [string]$EvidencePrefix = (Join-Path $PSScriptRoot "..\dist\clausis-acpi-soak"),
    [ValidateRange(2, 20)]
    [int]$Runs = 5,
    [int]$BootTimeoutSeconds = 180,
    [int]$DesktopTimeoutSeconds = 240,
    [int]$ShutdownTimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"
$smoke = Join-Path $PSScriptRoot "vbox_acpi_smoke.ps1"
if (-not (Test-Path -LiteralPath $smoke -PathType Leaf)) {
    throw "VirtualBox ACPI smoke harness was not found at $smoke"
}

$iso = (Resolve-Path -LiteralPath $IsoPath).Path
$vdi = (Resolve-Path -LiteralPath $ExpectedVdi).Path
$expectedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $iso).Hash.ToLowerInvariant()
$summaryPath = "$EvidencePrefix-summary.json"
$summaryDirectory = Split-Path -Parent $summaryPath
if ($summaryDirectory -and -not (Test-Path -LiteralPath $summaryDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $summaryDirectory | Out-Null
}

$results = [Collections.Generic.List[object]]::new()
$completed = $false
try {
    for ($run = 1; $run -le $Runs; $run++) {
        $runPrefix = "{0}-run{1:D2}" -f $EvidencePrefix, $run
        $result = & $smoke `
            -VmName $VmName `
            -IsoPath $iso `
            -ExpectedVdi $vdi `
            -EvidencePrefix $runPrefix `
            -BootTimeoutSeconds $BootTimeoutSeconds `
            -DesktopTimeoutSeconds $DesktopTimeoutSeconds `
            -ShutdownTimeoutSeconds $ShutdownTimeoutSeconds
        $resultItems = @($result)
        if ($resultItems.Count -ne 1) {
            throw "ACPI soak run $run returned no unique result"
        }
        $result = $resultItems[0]
        if ($result.IsoSha256 -ne $expectedHash) {
            throw "ACPI soak run $run used an unexpected ISO hash"
        }
        if ($result.FinalState -ne "poweroff") {
            throw "ACPI soak run $run did not finish in poweroff"
        }
        $results.Add([pscustomobject]@{
            Run = $run
            GrubReadySeconds = $result.GrubReadySeconds
            DesktopReadySeconds = $result.DesktopReadySeconds
            PoweroffSeconds = $result.PoweroffSeconds
            FinalState = $result.FinalState
        })
    }
    $completed = $true
}
finally {
    $poweroffValues = @($results | ForEach-Object { $_.PoweroffSeconds })
    [pscustomobject]@{
        VmName = $VmName
        IsoPath = $iso
        IsoSha256 = $expectedHash
        ExpectedVdi = $vdi
        RequestedRuns = $Runs
        CompletedRuns = $results.Count
        Passed = $completed -and $results.Count -eq $Runs
        MinimumPoweroffSeconds = if ($poweroffValues.Count) {
            [math]::Round(($poweroffValues | Measure-Object -Minimum).Minimum, 1)
        } else { $null }
        MaximumPoweroffSeconds = if ($poweroffValues.Count) {
            [math]::Round(($poweroffValues | Measure-Object -Maximum).Maximum, 1)
        } else { $null }
        Runs = @($results)
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $summaryPath -Encoding utf8
}

Get-Content -LiteralPath $summaryPath -Raw | ConvertFrom-Json
