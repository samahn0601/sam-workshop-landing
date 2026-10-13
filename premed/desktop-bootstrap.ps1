param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('collab', 'statsam')]
  [string]$Track,
  [string]$ManifestPath
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$BaseUrl = 'https://sam-workshop-landing.vercel.app/premed/'
$Root = [IO.Path]::GetFullPath((Get-Location).Path)
$ManifestUrl = "$BaseUrl`desktop-bootstrap.json"

function Get-JsonManifest {
  if ($ManifestPath) {
    return Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
  }
  $response = Invoke-WebRequest -Uri $ManifestUrl -UseBasicParsing
  $responseUri = $response.BaseResponse.ResponseUri
  if (-not $responseUri) { $responseUri = $response.BaseResponse.RequestMessage.RequestUri }
  if (-not $responseUri -or $responseUri.Scheme -ne 'https') { throw 'Manifest did not use HTTPS.' }
  return $response.Content | ConvertFrom-Json
}

function Get-Sha256([string]$Path) {
  $sha = [Security.Cryptography.SHA256]::Create()
  $stream = [IO.File]::OpenRead($Path)
  try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
  finally { $stream.Dispose(); $sha.Dispose() }
}

function Get-ProgramVersion([string[]]$Candidates) {
  foreach ($candidate in $Candidates) {
    $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    try {
      $arguments = if ($candidate -eq 'py') { @('-3', '--version') } else { @('--version') }
      $versionResult = Invoke-NativeCaptured $cmd.Source $arguments
      $line = $versionResult.Output
      if ($line -match 'Python\s+(\d+\.\d+)') {
        $v = [Version]$Matches[1]
        if ($v -ge [Version]$script:MinimumPython) { return @{ Path = $cmd.Source; Version = $Matches[1]; Launcher = ($candidate -eq 'py') } }
      }
    } catch {}
  }
  return $null
}

function Invoke-NativeCaptured([string]$FilePath, [string[]]$Arguments) {
  $previousPreference = $ErrorActionPreference
  try {
    # Windows PowerShell 5.1 can turn native stderr into a terminating error.
    # Capture it as text and use the process exit code to determine success.
    $ErrorActionPreference = 'Continue'
    $captured = (& $FilePath @Arguments 2>&1 | Out-String).Trim()
    $exitCode = $LASTEXITCODE
    return [pscustomobject]@{ Output = $captured; ExitCode = $exitCode }
  } finally {
    $ErrorActionPreference = $previousPreference
  }
}

function Assert-ZipSafe([string]$ZipPath, [string]$Destination) {
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $dest = [IO.Path]::GetFullPath($Destination).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
  $archive = [IO.Compression.ZipFile]::OpenRead($ZipPath)
  try {
    foreach ($entry in $archive.Entries) {
      $name = $entry.FullName
      if (-not $name -or $name.StartsWith('/') -or $name.Contains('\') -or $name -match '(^|/)\.\.?(/|$)') { throw "Unsafe ZIP member path: $name" }
      $resolved = [IO.Path]::GetFullPath((Join-Path $Destination $name))
      if (-not $resolved.StartsWith($dest, [StringComparison]::OrdinalIgnoreCase)) { throw "ZIP member escapes target folder: $name" }
      $unixType = ([int]$entry.ExternalAttributes -shr 16) -band 0xF000
      if ($unixType -eq 0xA000) { throw "ZIP symbolic links are not allowed: $name" }
    }
  } finally { $archive.Dispose() }
}

function Expand-ZipSafe([string]$ZipPath, [string]$Destination) {
  Assert-ZipSafe $ZipPath $Destination
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  [IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $Destination)
}

function Get-Uv([string]$ToolDir, $Runtime) {
  $assetKey = switch ([Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()) {
    'X64' { 'windows_x64' }
    'Arm64' { 'windows_arm64' }
    'X86' { 'windows_x86' }
    default { throw "Unsupported Windows architecture: $($_)" }
  }
  $asset = $Runtime.uv_assets.$assetKey
  if (-not $asset -or $asset.sha256 -notmatch '^[0-9a-f]{64}$') { throw "No pinned uv SHA-256 is available for $assetKey." }
  $assetName = [string]$asset.file
  $zip = Join-Path $ToolDir $assetName
  Invoke-WebRequest -Uri ($Runtime.uv_release_base + $assetName) -OutFile $zip -UseBasicParsing
  $actual = Get-Sha256 $zip
  if ($actual -ne $asset.sha256) { throw 'uv checksum mismatch; refusing to run the downloaded tool.' }
  $uvRoot = Join-Path $ToolDir 'uv-unpacked'
  New-Item -ItemType Directory -Path $uvRoot | Out-Null
  Expand-ZipSafe $zip $uvRoot
  $uv = Get-ChildItem -LiteralPath $uvRoot -Filter 'uv.exe' -File -Recurse | Select-Object -First 1
  if (-not $uv) { throw 'Verified uv archive did not contain uv.exe.' }
  return $uv.FullName
}

try {
  $manifest = Get-JsonManifest
  $script:MinimumPython = [string]$manifest.runtime.minimum_python
  $trackInfo = $manifest.tracks.$Track
  if (-not $trackInfo -or $trackInfo.sha256 -notmatch '^[0-9a-f]{64}$' -or -not $trackInfo.bytes) {
    throw "The '$Track' package is not ready in the published manifest. Ask the instructor for the current bundle link."
  }
  if ($trackInfo.url -notmatch '^https://sam-workshop-landing\.vercel\.app/premed/') { throw 'Package URL is outside the workshop HTTPS host.' }

  $unexpected = @(Get-ChildItem -LiteralPath $Root -Force | Where-Object { $_.Name -ne '.bootstrap' })
  if ($unexpected.Count -gt 0) { throw 'The selected folder is not empty. Choose a new dedicated folder; nothing was overwritten.' }
  $stateDir = Join-Path $Root '.bootstrap'
  if (Test-Path -LiteralPath $stateDir) {
    $allowedBootstrap = @('desktop-bootstrap.json', 'desktop-bootstrap.ps1', 'desktop-bootstrap.sh')
    $unexpectedBootstrap = @(Get-ChildItem -LiteralPath $stateDir -Force | Where-Object { $_.Name -notin $allowedBootstrap })
    if ($unexpectedBootstrap.Count -gt 0) { throw 'The .bootstrap folder contains unexpected files; nothing was overwritten.' }
  }

  $target = Join-Path $Root $trackInfo.target_directory
  if (Test-Path -LiteralPath $target) { throw "Target already exists; nothing was overwritten: $target" }
  New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
  $download = Join-Path $stateDir $trackInfo.archive
  Invoke-WebRequest -Uri $trackInfo.url -OutFile $download -UseBasicParsing
  $actualBytes = (Get-Item -LiteralPath $download).Length
  if ($actualBytes -ne [long]$trackInfo.bytes) { throw "Package size mismatch ($actualBytes bytes); refusing to extract." }
  $actualHash = Get-Sha256 $download
  if ($actualHash -ne $trackInfo.sha256) { throw 'Package SHA-256 mismatch; refusing to extract.' }

  New-Item -ItemType Directory -Path $target | Out-Null
  Expand-ZipSafe $download $target
  foreach ($required in $trackInfo.required_files) {
    if (-not (Test-Path -LiteralPath (Join-Path $target $required) -PathType Leaf)) { throw "Required package file is missing: $required" }
  }
  Write-Output "BUNDLE_READY track=$Track package_sha256=$actualHash"

  $python = Get-ProgramVersion @('py', 'python', 'python3')
  $managed = $false
  $uv = $null
  if (-not $python) {
    $uv = Get-Uv $stateDir $manifest.runtime
  }

  if ($python) {
    if ($python.Launcher) { $probe = Invoke-NativeCaptured $python.Path @('-3', '-c', 'import venv, ensurepip') }
    else { $probe = Invoke-NativeCaptured $python.Path @('-c', 'import venv, ensurepip') }
    if ($probe.ExitCode -ne 0) {
      Write-Output 'Existing Python lacks venv/ensurepip; using the pinned project-local runtime.'
      $python = $null
      if (-not $uv) { $uv = Get-Uv $stateDir $manifest.runtime }
    }
  }
  if (-not $python) {
    if (-not $uv) { $uv = Get-Uv $stateDir $manifest.runtime }
    $runtimeDir = Join-Path $Root '.runtime\python'
    $env:UV_PYTHON_INSTALL_DIR = $runtimeDir
    $env:UV_PYTHON_INSTALL_BIN = '0'
    $env:UV_PYTHON_INSTALL_REGISTRY = '0'
    $env:UV_PYTHON_NO_REGISTRY = '1'
    $env:UV_CACHE_DIR = Join-Path $Root '.runtime\cache'
    $installResult = Invoke-NativeCaptured $uv @('python', 'install', [string]$manifest.runtime.managed_python_minor, '--no-bin', '--no-registry')
    if ($installResult.ExitCode -ne 0) { throw "uv could not install a local Python runtime. $($installResult.Output)" }
    $findResult = Invoke-NativeCaptured $uv @('python', 'find', [string]$manifest.runtime.managed_python_minor, '--managed-python')
    $pythonPath = $findResult.Output
    if ($findResult.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) { throw "Could not locate the local Python runtime after installation. $pythonPath" }
    $python = @{ Path = $pythonPath; Version = $manifest.runtime.managed_python_minor; Args = @() }
    $managed = $true
  }
  if ($Track -eq 'statsam') {
    if (-not $uv) { $uv = Get-Uv $stateDir $manifest.runtime }
    $env:PATH = (Split-Path -Parent $uv) + [IO.Path]::PathSeparator + $env:PATH
  }

  $venv = Join-Path $target '.venv'
  if ($python.Launcher) { $venvResult = Invoke-NativeCaptured $python.Path @('-3', '-m', 'venv', $venv) }
  else { $venvResult = Invoke-NativeCaptured $python.Path @('-m', 'venv', $venv) }
  if ($venvResult.ExitCode -ne 0) { throw "Python was found, but the workshop virtual environment could not be created. $($venvResult.Output)" }
  $venvPython = Join-Path $venv 'Scripts\python.exe'
  if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) { throw 'The virtual environment interpreter was not created.' }
  $versionResult = Invoke-NativeCaptured $venvPython @('--version')
  $versionLine = $versionResult.Output
  if ($versionResult.ExitCode -ne 0) { throw "Could not read the virtual environment Python version. $versionLine" }
  if ($versionLine -notmatch 'Python\s+(\d+\.\d+)' -or [Version]$Matches[1] -lt [Version]$manifest.runtime.minimum_python) { throw "Unsupported Python runtime: $versionLine" }

  $analysisChecks = @()
  if ($Track -eq 'collab') {
    $doctorResult = Invoke-NativeCaptured $venvPython @('-X', 'utf8', (Join-Path $target 'pipeline.py'), 'doctor')
    $doctorRaw = $doctorResult.Output
    if ($doctorResult.ExitCode -ne 0) { throw "Collab doctor failed: $doctorRaw" }
    try { $doctor = $doctorRaw | ConvertFrom-Json } catch { throw "Collab doctor did not return valid JSON: $doctorRaw" }
    foreach ($check in @('python_supported', 'write_read_korean', 'core_hashes_match', 'path_ok', 'folder_ok')) {
      if ($doctor.$check -ne $true) { throw "Collab doctor check '$check' did not pass. bundle_ready=true, analysis_ready=false. $doctorRaw" }
    }
    $analysisChecks += 'pipeline_doctor=PASS'
  } else {
    $bootstrap = Join-Path $target 'bootstrap.py'
    foreach ($step in @('setup', 'doctor', 'verify')) {
      $stepResult = Invoke-NativeCaptured $venvPython @('-X', 'utf8', $bootstrap, $step)
      $stepOutput = $stepResult.Output
      if ($stepResult.ExitCode -ne 0) { throw "StatSam $step failed: $stepOutput. bundle_ready=true, analysis_ready=false." }
      Write-Output "STATSam_$($step.ToUpperInvariant())_PASS"
      $analysisChecks += "statsam_$step=PASS"
    }
  }

  $report = [ordered]@{
    completed_utc = [DateTime]::UtcNow.ToString('o')
    track = $Track
    package = $trackInfo.archive
    sha256 = $actualHash
    extracted_to = $target
    python = $versionLine
    python_source = $(if ($managed) { 'uv-managed, workspace-local' } else { 'existing interpreter; venv workspace-local' })
    interpreter = $venvPython
    bundle_ready = $true
    analysis_ready = $true
    analysis_checks = ($analysisChecks -join ',')
  }
  @(
    "completed_utc=$($report.completed_utc)"
    "track=$($report.track)"
    "package=$($report.package)"
    "sha256=$($report.sha256)"
    "extracted_to=$($report.extracted_to)"
    "python=$($report.python)"
    "python_source=$($report.python_source)"
    "interpreter=$($report.interpreter)"
    "bundle_ready=$($report.bundle_ready)"
    "analysis_ready=$($report.analysis_ready)"
    "analysis_checks=$($report.analysis_checks)"
  ) | Set-Content -LiteralPath (Join-Path $Root 'WORKSHOP_SETUP.txt') -Encoding UTF8
  Write-Output "SETUP_OK track=$Track package_sha256=$actualHash bundle_ready=true analysis_ready=true python=$versionLine"
  Write-Output "Track folder: $target"
  Write-Output "Use this interpreter for workshop commands: $venvPython"
} catch {
  Write-Error $_
  exit 1
}
