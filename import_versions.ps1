# === CONFIGURATION ===
$ProjectPath = "D:\Работы\_FR\Каунтер TVT\camera-receiver-server"
$VersionsPath = "$ProjectPath\versions"
$MainFile = "$ProjectPath\server.py"

cd $ProjectPath

# Check repo
if (-not (Test-Path "$ProjectPath\.git")) {
    Write-Host "Git repo not found. Run 'git init' first." -ForegroundColor Red
    exit
}

# Sort files naturally: 01_, 02_...
$files = Get-ChildItem $VersionsPath -Filter *.py | Sort-Object Name

$counter = 1

foreach ($file in $files) {

    $versionName = [IO.Path]::GetFileNameWithoutExtension($file.Name)

    # FIX: PowerShell doesn't allow ":" right after $counter
    $commitMessage = "Version ${counter}: $versionName"
    $tag = "v$($counter).0"

    Write-Host "Processing $file → $MainFile" -ForegroundColor Cyan
    
    # overwrite main script with this version
    Copy-Item $file.FullName $MainFile -Force

    # add to git
    git add server.py

    # commit
    git commit -m "$commitMessage"

    # tag
    git tag $tag

    $counter++
}

Write-Host "Done! Now push:" -ForegroundColor Green
Write-Host "   git push"
Write-Host "   git push --tags"
