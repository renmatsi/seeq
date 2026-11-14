Add-Type -AssemblyName WindowsBase, PresentationCore
$ErrorActionPreference = 'Stop'

$source = (Resolve-Path -LiteralPath "$PSScriptRoot/../interface/brand-icon.png").Path
$artwork = [Windows.Media.Imaging.BitmapFrame]::Create([Uri]::new($source))

function Render-Icon([int] $size) {
    $visual = [Windows.Media.DrawingVisual]::new()
    [Windows.Media.RenderOptions]::SetBitmapScalingMode($visual, [Windows.Media.BitmapScalingMode]::HighQuality)
    $drawing = $visual.RenderOpen()
    try {
        $scale = $size / [Math]::Max($artwork.PixelWidth, $artwork.PixelHeight)
        $width = $artwork.PixelWidth * $scale
        $height = $artwork.PixelHeight * $scale
        $drawing.DrawImage($artwork, [Windows.Rect]::new(($size - $width) / 2, ($size - $height) / 2, $width, $height))
    } finally {
        $drawing.Close()
    }
    $bitmap = [Windows.Media.Imaging.RenderTargetBitmap]::new(
        $size, $size, 96, 96, [Windows.Media.PixelFormats]::Pbgra32)
    $bitmap.Render($visual)
    $encoder = [Windows.Media.Imaging.PngBitmapEncoder]::new()
    $encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
    $stream = [IO.MemoryStream]::new()
    try {
        $encoder.Save($stream)
        return ,($stream.ToArray())
    } finally {
        $stream.Dispose()
    }
}

$sizes = 16, 20, 24, 32, 40, 48, 64, 96, 128, 256
$frames = foreach ($size in $sizes) {
    [PSCustomObject]@{ Size = $size; Data = (Render-Icon $size) }
}
$output = [IO.File]::Create("$PSScriptRoot/torrentFindr.ico")
$ico = [IO.BinaryWriter]::new($output)
try {
    $ico.Write([uint16]0)
    $ico.Write([uint16]1)
    $ico.Write([uint16]$frames.Count)
    $offset = 6 + 16 * $frames.Count
    foreach ($frame in $frames) {
        $sizeByte = [byte]($frame.Size % 256)
        $ico.Write($sizeByte)
        $ico.Write($sizeByte)
        $ico.Write([uint16]0)
        $ico.Write([uint16]1)
        $ico.Write([uint16]32)
        $ico.Write([uint32]$frame.Data.Length)
        $ico.Write([uint32]$offset)
        $offset += $frame.Data.Length
    }
    foreach ($frame in $frames) {
        $ico.Write([byte[]]$frame.Data)
    }
} finally {
    $ico.Dispose()
}
[IO.File]::WriteAllBytes("$PSScriptRoot/torrentFindr-icon.png", (Render-Icon 512))
