param (
    [Parameter(Mandatory = $false)]
    [ValidateSet("global", "project")]
    [string]$Target = "global",

    [Parameter(Mandatory = $false)]
    [string]$ProjectPath = "",

    [Parameter(Mandatory = $false)]
    [string]$SkillName = ""
)

$RepoRoot = (Get-Item $PSScriptRoot).Parent.FullName
$SkillsDir = Join-Path $RepoRoot "skills"

if (-not (Test-Path $SkillsDir)) {
    Write-Error "Could not find 'skills' folder at $SkillsDir"
    exit 1
}

# Determine destination dot-agents folder
if ($Target -eq "global") {
    $UserProfile = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::UserProfile)
    $DestDotDir = Join-Path $UserProfile ".gemini\config"
} else {
    if (-not $ProjectPath) {
        Write-Error "Please provide -ProjectPath when -Target is 'project'"
        exit 1
    }
    $DestDotDir = Join-Path $ProjectPath ".agents"
}

$DestSkillsDir = Join-Path $DestDotDir "skills"
if (-not (Test-Path $DestSkillsDir)) {
    New-Item -ItemType Directory -Path $DestSkillsDir -Force | Out-Null
}

$SkillsToInstall = @()
if ($SkillName) {
    $TargetSkillPath = Join-Path $SkillsDir $SkillName
    if (-not (Test-Path $TargetSkillPath)) {
        Write-Error "Skill '$SkillName' not found under $SkillsDir"
        exit 1
    }
    $SkillsToInstall += (Get-Item $TargetSkillPath)
} else {
    $SkillsToInstall = Get-ChildItem -Directory -Path $SkillsDir
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Installing Skills from: $SkillsDir" -ForegroundColor Cyan
Write-Host " Target Scope:          $Target" -ForegroundColor Cyan
Write-Host " Destination:           $DestSkillsDir" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

foreach ($skill in $SkillsToInstall) {
    $dest = Join-Path $DestSkillsDir $skill.Name
    Write-Host "Installing skill: $($skill.Name) -> $dest" -ForegroundColor Green
    Copy-Item -Path $skill.FullName -Destination $DestSkillsDir -Recurse -Force
}

Write-Host "`nInstallation complete! Installed $($SkillsToInstall.Count) skill(s)." -ForegroundColor Yellow
if ($Target -eq "global") {
    Write-Host "These skills are now accessible globally across all Antigravity workspaces." -ForegroundColor Gray
} else {
    Write-Host "These skills are now accessible in project: $ProjectPath" -ForegroundColor Gray
}

