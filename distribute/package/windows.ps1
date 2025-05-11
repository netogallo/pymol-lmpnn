# Install mysys2
$tmp_file = [System.IO.Path]::GetTempFileName()
$mysys2 = "$tmp_file.exe"
Invoke-WebRequest -Uri "https://repo.msys2.org/distrib/msys2-x86_64-latest.exe" -OutFile "$mysys2"

$tempRoot = [System.IO.Path]::GetTempPath()
$tempName = [System.IO.Path]::GetRandomFileName()
$mysys2_root = Join-Path $tempRoot $tempName

echo "installer: $mysys2"

& "$mysys2" in --confirm-command --accept-messages --root "$mysys2_root"

# Finish the job in mysys2
$cygpath = "$mysys2_root\usr\bin\cygpath.exe"
$current_dir = Get-Location
$dir = & "$cygpath" "$current_dir"
$script = & "$cygpath" "$dir\distribute\package\windows.sh"

& "$mysys2_root\usr\bin\bash" --login "$script" "$dir"
