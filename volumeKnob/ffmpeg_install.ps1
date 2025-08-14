# Get the directory of the currently running script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Define the path to the existing FFmpeg folder using a relative path
$existingFfmpegPath = Join-Path -Path $scriptDir -ChildPath "ffmpeg"

# Define the destination path
$destinationPath = "C:\ffmpeg"

# Check if the destination directory exists; if not, create it
if (-Not (Test-Path $destinationPath)) {
    New-Item -ItemType Directory -Path $destinationPath
}

# Move the existing FFmpeg to the desired location
if (Test-Path $existingFfmpegPath) {
    Move-Item -Path "$existingFfmpegPath\*" -Destination $destinationPath -Force
    Write-Host "FFmpeg moved successfully to $destinationPath."
} else {
    Write-Host "FFmpeg folder not found at $existingFfmpegPath."
    exit
}

# Update the system PATH (requires admin privileges)
$path = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::Machine)
if ($path -notlike "*C:\ffmpeg\bin*") {
    [System.Environment]::SetEnvironmentVariable("Path", "$path;C:\ffmpeg\bin", [System.EnvironmentVariableTarget]::Machine)
    Write-Host "System PATH updated successfully."
} else {
    Write-Host "C:\ffmpeg\bin is already in the PATH."
}

Write-Host "FFmpeg installation process completed. Please restart your terminal."