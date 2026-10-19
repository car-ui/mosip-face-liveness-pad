[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [string]$SourceDirectory = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
$sourceRoot = (Resolve-Path -LiteralPath $SourceDirectory).Path
$outputRoot = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$runName = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$checkOutput = Join-Path $outputRoot $runName
New-Item -ItemType Directory -Path $checkOutput | Out-Null
$checkVariables = @('TEMP', 'TMP', 'PYTHONPYCACHEPREFIX', 'OPENCV_FOR_THREADS_NUM')
$previousEnvironment = @{}
foreach ($name in $checkVariables) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$report = [ordered]@{
    schemaVersion = 1
    startedAtUtc = [DateTime]::UtcNow.ToString('o')
    source = $sourceRoot
    outputDirectory = $checkOutput
    status = 'RUNNING'
    scope = 'Python regression checks. No physical attack, identity matching or native UI claim.'
}
$exitStatus = 1
$locationPushed = $false
try {
    $temporaryDirectory = Join-Path $checkOutput 'tmp'
    New-Item -ItemType Directory -Path $temporaryDirectory -Force | Out-Null
    [Environment]::SetEnvironmentVariable('TEMP', $temporaryDirectory, 'Process')
    [Environment]::SetEnvironmentVariable('TMP', $temporaryDirectory, 'Process')
    [Environment]::SetEnvironmentVariable('PYTHONPYCACHEPREFIX', (Join-Path $checkOutput 'pycache'), 'Process')
    [Environment]::SetEnvironmentVariable('OPENCV_FOR_THREADS_NUM', '1', 'Process')
    Push-Location -LiteralPath $sourceRoot
    $locationPushed = $true
    if (Test-Path -LiteralPath (Join-Path $sourceRoot '.git')) {
        $report.commit = (& git rev-parse HEAD).Trim()
        $report.dirty = [bool](& git status --porcelain --untracked-files=no)
    } elseif (Test-Path -LiteralPath (Join-Path $sourceRoot 'RELEASE_MANIFEST.json')) {
        $report.declaredPackageCommit = (Get-Content -LiteralPath 'RELEASE_MANIFEST.json' -Raw | ConvertFrom-Json).commit
    }
    $runtimeLog = Join-Path $checkOutput 'python-runtime.txt'
    & $Python -c 'import sys; print(sys.version); print(sys.executable); print(sys.base_prefix)' 2>&1 |
        Tee-Object -FilePath $runtimeLog
    if ($LASTEXITCODE -ne 0) { throw 'The selected Python runtime did not start.' }
    $junit = Join-Path $checkOutput 'pytest.xml'
    $pytestLog = Join-Path $checkOutput 'pytest.log'
    & $Python -X faulthandler -m pytest -q -p no:cacheprovider "--junitxml=$junit" 2>&1 |
        Tee-Object -FilePath $pytestLog
    $exitStatus = $LASTEXITCODE
    $report.pytestExitCode = $exitStatus
    if ($exitStatus -ne 0) { throw 'Python regression checks did not pass. See pytest.log.' }
    [xml]$results = Get-Content -LiteralPath $junit -Raw
    $suite = $results.testsuites.testsuite
    $report.tests = [int]$suite.tests
    $report.failures = [int]$suite.failures
    $report.errors = [int]$suite.errors
    $report.skipped = [int]$suite.skipped
    $report.passed = $report.tests - $report.failures - $report.errors - $report.skipped
    if ($report.passed -lt 1 -or $report.failures -ne 0 -or $report.errors -ne 0) {
        $exitStatus = 1
        throw 'The result does not establish a complete passing regression run.'
    }
    $report.status = 'PASS'
    $report.logSha256 = (Get-FileHash -LiteralPath $pytestLog -Algorithm SHA256).Hash.ToLowerInvariant()
    $report.junitSha256 = (Get-FileHash -LiteralPath $junit -Algorithm SHA256).Hash.ToLowerInvariant()
} catch {
    $report.status = 'FAIL'
    $report.error = $_.Exception.Message
    $exitStatus = 1
    Write-Warning $report.error
} finally {
    if ($locationPushed) { Pop-Location }
    foreach ($name in $checkVariables) {
        [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process')
    }
    $report.finishedAtUtc = [DateTime]::UtcNow.ToString('o')
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $checkOutput 'result.json') -Encoding utf8
    Write-Output ('Check report: ' + (Join-Path $checkOutput 'result.json'))
}
exit $exitStatus
