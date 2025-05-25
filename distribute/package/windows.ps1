# Install mysys2
$tmp_file = [System.IO.Path]::GetTempFileName()
$msys2 = "$tmp_file.exe"

Invoke-WebRequest -Uri "https://repo.msys2.org/distrib/msys2-x86_64-latest.exe" -OutFile "$msys2"

$tempRoot = [System.IO.Path]::GetTempPath()
$tempName = [System.IO.Path]::GetRandomFileName()
$msys2_root = Join-Path $tempRoot $tempName

echo "installer: $msys2"
& "$msys2" in --confirm-command --accept-messages --root "$msys2_root"

# Get out of powershell and finish
# the job with msys2
$cygpath = "$msys2_root\usr\bin\cygpath.exe"
$current_dir = Get-Location
$dir = & "$cygpath" "$current_dir"
$script = & "$cygpath" "$dir\distribute\package\windows.sh"

& "$msys2_root\usr\bin\bash" --login "$script" "$dir"
