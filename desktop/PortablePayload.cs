using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;

internal static class PortablePayload
{
    private const string Resource = "torrentFindr.Payload.zip";
    private static readonly Assembly App = typeof(PortablePayload).Assembly;

    internal static bool IsEmbedded => App.GetManifestResourceInfo(Resource) is not null;

    internal static string Extract()
    {
        var local = Environment.GetEnvironmentVariable("LOCALAPPDATA")
            ?? Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var root = Path.GetFullPath(Path.Combine(local, "seeq", "standalone"));
        Directory.CreateDirectory(root);
        var version = App.ManifestModule.ModuleVersionId.ToString("N");
        var destination = Path.Combine(root, version);
        var lockPath = Path.Combine(root, version + ".lock");
        using var extractionLock = WaitForLock(lockPath);
        if (IsReady(destination)) return destination;

        var staging = Path.Combine(root, version + "-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        try
        {
            using var resource = App.GetManifestResourceStream(Resource)
                ?? throw new InvalidOperationException("Os arquivos internos do aplicativo estão ausentes.");
            using var zip = new ZipArchive(resource, ZipArchiveMode.Read);
            zip.ExtractToDirectory(staging);
            GrantRuntimeAccess(Path.Combine(staging, "webview2-runtime"));
            File.WriteAllText(Path.Combine(staging, ".complete"), version);
            if (!IsReady(staging))
                throw new InvalidDataException("O pacote interno está incompleto.");
            if (Directory.Exists(destination))
                Directory.Move(destination, staging + ".old");
            Directory.Move(staging, destination);
        }
        finally
        {
            if (Directory.Exists(staging)) Directory.Delete(staging, recursive: true);
        }
        return destination;
    }

    private static FileStream WaitForLock(string path)
    {
        var deadline = Environment.TickCount64 + 120_000;
        while (true)
        {
            try { return File.Open(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None); }
            catch (IOException error) when ((error.HResult & 0xffff) == 32 && Environment.TickCount64 < deadline)
            {
                Thread.Sleep(250);
            }
        }
    }

    private static bool IsReady(string path) =>
        File.Exists(Path.Combine(path, ".complete")) &&
        File.Exists(Path.Combine(path, "engine", "python.exe")) &&
        File.Exists(Path.Combine(path, "webview2-runtime", "msedgewebview2.exe")) &&
        File.Exists(Path.Combine(path, "browser", "TorrentFindr.Browser.exe")) &&
        File.Exists(Path.Combine(path, "desktop_backend.py")) &&
        File.Exists(Path.Combine(path, "interface", "index.html"));

    private static void GrantRuntimeAccess(string runtime)
    {
        // The WebView2 renderer runs in an AppContainer and needs read access to these binaries.
        var start = new ProcessStartInfo(Path.Combine(Environment.SystemDirectory, "icacls.exe"))
        {
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        start.ArgumentList.Add(runtime);
        start.ArgumentList.Add("/grant");
        start.ArgumentList.Add("*S-1-15-2-1:(OI)(CI)(RX)");
        start.ArgumentList.Add("*S-1-15-2-2:(OI)(CI)(RX)");
        using var process = Process.Start(start)
            ?? throw new IOException("Não foi possível preparar as permissões da interface.");
        process.WaitForExit();
        if (process.ExitCode != 0)
            throw new IOException("Não foi possível preparar as permissões da interface.");
    }
}
