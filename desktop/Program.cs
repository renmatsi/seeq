using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        if (PortablePayload.IsEmbedded)
        {
            using var portable = new DesktopWindow();
            Application.Run(portable);
            return;
        }
        var project = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, ".."));
        var worker = Path.Combine(project, "engine", "torrentFindr-engine.exe");
        var packed = File.Exists(worker);
        if (!packed && args.Length != 1)
        {
            MessageBox.Show("Abra o seeq pelo Iniciar.bat.", "seeq");
            return;
        }
        using var window = new DesktopWindow(project, packed ? worker : args[0], packed);
        Application.Run(window);
    }
}

internal sealed class DesktopWindow : Form
{
    private const string Host = "seeq.local";
    private const string Origin = "https://" + Host + "/";
    private string project;
    private string executable;
    private readonly bool packed;
    private readonly bool standalone;
    private readonly Icon appIcon;
    private readonly WebView2 view = new() { Dock = DockStyle.Fill, DefaultBackgroundColor = Color.FromArgb(32,33,36) };
    private readonly StartupPrompt loading = new();
    private readonly System.Windows.Forms.Timer startupTimeout = new() { Interval = 30_000 };
    private Process? worker;
    private bool closed;
    private bool startupFailed;
    private bool nativeDrag;

    [DllImport("user32.dll")]
    private static extern bool ReleaseCapture();
    [DllImport("user32.dll")]
    private static extern IntPtr SendMessageW(IntPtr handle, uint message, IntPtr wparam, IntPtr lparam);
    [DllImport("user32.dll")]
    private static extern bool ShowWindow(IntPtr handle, int command);
    [DllImport("dwmapi.dll")]
    private static extern int DwmSetWindowAttribute(IntPtr handle, int attribute, ref uint value, int size);

    internal DesktopWindow(string project = "", string executable = "", bool packed = false)
    {
        this.project = project;
        this.executable = executable;
        this.packed = packed;
        standalone = project.Length == 0;
        Text = "seeq";
        MaximizeBox = false;
        using var iconData = typeof(DesktopWindow).Assembly.GetManifestResourceStream("torrentFindr.WindowIcon.ico")!;
        appIcon = new Icon(iconData);
        Icon = appIcon;
        StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(1000, 850);
        MinimumSize = new Size(690, 510);
        BackColor = view.DefaultBackgroundColor;
        Controls.Add(view);
        Controls.Add(loading);
        loading.BringToFront();
        startupTimeout.Tick += (_, _) => FailStartup("A interface não respondeu durante a inicialização.");
        Shown += async (_, _) =>
        {
            var area = Screen.FromHandle(Handle).WorkingArea;
            double scale = DeviceDpi / 96.0;
            int width = Math.Min((int)Math.Round(1000*scale),area.Width);
            int height = Math.Min((int)Math.Round(850*scale),area.Height);
            Bounds = new Rectangle(area.Left+(area.Width-width)/2,area.Top+(area.Height-height)/2,width,height);
            await Initialize();
        };
    }

    protected override CreateParams CreateParams
    {
        get
        {
            var parameters = base.CreateParams;
            parameters.Style |= 0x00CE0000; // Caption, system menu, resizable frame and minimize box.
            return parameters;
        }
    }

    protected override void OnHandleCreated(EventArgs e)
    {
        base.OnHandleCreated(e);
        uint rounded = 2;
        uint noBorder = 0xfffffffe;
        DwmSetWindowAttribute(Handle, 33, ref rounded, sizeof(uint));
        DwmSetWindowAttribute(Handle, 34, ref noBorder, sizeof(uint));
    }

    protected override void WndProc(ref Message message)
    {
        if (message.Msg == 0x112 && (message.WParam.ToInt64() & 0xFFF0) == 0xF030) // WM_SYSCOMMAND / SC_MAXIMIZE
        {
            message.Result = IntPtr.Zero;
            return;
        }
        if (message.Msg == 0x05 && message.WParam == (IntPtr)2) // WM_SIZE / SIZE_MAXIMIZED
        {
            ShowWindow(message.HWnd, 9); // SW_RESTORE also handles direct Windows API requests.
            message.Result = IntPtr.Zero;
            return;
        }
        if (message.Msg == 0x83) // WM_NCCALCSIZE
        {
            message.Result = IntPtr.Zero;
            return;
        }
        if (message.Msg == 0x84 && WindowState == FormWindowState.Normal) // WM_NCHITTEST
        {
            var bits = message.LParam.ToInt64();
            int x = unchecked((short)bits), y = unchecked((short)(bits >> 16));
            var bounds = Bounds;
            int edge = Math.Max(5, DeviceDpi * 6 / 96);
            bool left = x < bounds.Left + edge, right = x >= bounds.Right - edge;
            bool top = y < bounds.Top + edge, bottom = y >= bounds.Bottom - edge;
            var hit = top ? (left ? 13 : right ? 14 : 12)
                : bottom ? (left ? 16 : right ? 17 : 15)
                : left ? 10 : right ? 11 : 0;
            if (hit != 0)
            {
                message.Result = (IntPtr)hit;
                return;
            }
        }
        base.WndProc(ref message);
    }

    private async Task Initialize()
    {
        try
        {
            if (standalone)
            {
                loading.Step("pacote.preparar()");
                project = await Task.Run(PortablePayload.Extract);
                if (closed) return;
                executable = Path.Combine(project, "engine", "python.exe");
                // Both windows must use the bundled runtime, even if an environment override is set.
                Environment.SetEnvironmentVariable("WEBVIEW2_BROWSER_EXECUTABLE_FOLDER",
                    Path.Combine(project, "webview2-runtime"));
            }
            var data = Path.Combine(Environment.GetEnvironmentVariable("APPDATA")
                ?? Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "torrentFindr");
            var fixedRuntime = Path.Combine(project, "webview2-runtime");
            var browserProfile = standalone ? "seeq-webview2-standalone" : "seeq-webview2";
            loading.Step("webview.iniciar()");
            var environment = await CoreWebView2Environment.CreateAsync(
                Directory.Exists(fixedRuntime) ? fixedRuntime : null, Path.Combine(data, browserProfile));
            if (closed) return;
            await view.EnsureCoreWebView2Async(environment);
            if (closed) return;
            view.ZoomFactor = 1;
            var browser = view.CoreWebView2;
            browser.Settings.AreDevToolsEnabled = false;
            browser.Settings.AreDefaultContextMenusEnabled = false;
            browser.Settings.IsZoomControlEnabled = false;
            browser.Settings.AreBrowserAcceleratorKeysEnabled = false;
            try
            {
                browser.Settings.IsNonClientRegionSupportEnabled = true;
                nativeDrag = true;
            }
            catch (NotImplementedException) { }
            catch (COMException) { }
            browser.SetVirtualHostNameToFolderMapping(Host, Path.Combine(project, "interface"),
                CoreWebView2HostResourceAccessKind.Deny);
            browser.NavigationStarting += (_, e) => e.Cancel = !e.Uri.StartsWith(Origin, StringComparison.Ordinal);
            browser.NewWindowRequested += (_, e) => e.Handled = true;
            browser.PermissionRequested += (_, e) => e.State = CoreWebView2PermissionState.Deny;
            browser.NavigationCompleted += (_, e) =>
            {
                if (!e.IsSuccess && loading.Visible) FailStartup("Não foi possível carregar a interface.");
            };
            browser.WebMessageReceived += Receive;
            loading.Step("busca.iniciar()");
            StartWorker();
            loading.Step("perfil.carregar()");
            startupTimeout.Start();
            browser.Navigate(Origin + "index.html");
        }
        catch (Exception error)
        {
            FailStartup(error.Message);
        }
    }

    private void FailStartup(string message)
    {
        if (closed || startupFailed) return;
        startupFailed = true;
        startupTimeout.Stop();
        MessageBox.Show(this, message, "seeq", MessageBoxButtons.OK, MessageBoxIcon.Error);
        Close();
    }

    private void StartWorker()
    {
        var start = new ProcessStartInfo(executable)
        {
            WorkingDirectory = project,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            StandardInputEncoding = new UTF8Encoding(false),
            StandardOutputEncoding = new UTF8Encoding(false),
        };
        if (!packed)
        {
            start.ArgumentList.Add("-B");
            start.ArgumentList.Add(Path.Combine(project, "desktop_backend.py"));
        }
        start.Environment["PYTHONIOENCODING"] = "utf-8";
        worker = Process.Start(start) ?? throw new InvalidOperationException("O mecanismo de busca não iniciou.");
        worker.StandardInput.AutoFlush = true;
        _ = ReadWorker(worker);
    }

    private async Task ReadWorker(Process process)
    {
        try
        {
            while (!closed && await process.StandardOutput.ReadLineAsync() is { } line)
            {
                if (line.Length <= 8_000_000) Send(line);
            }
        }
        catch (Exception) when (closed) { }
        if (closed) return;
        if (loading.Visible) FailStartup("O mecanismo de busca foi encerrado durante a inicialização.");
        else Send("{\"type\":\"status\",\"message\":\"O mecanismo de busca foi encerrado. Reabra o aplicativo.\"}");
    }

    private void Send(string json)
    {
        if (!closed && view.CoreWebView2 is { } browser)
        {
            try { browser.PostWebMessageAsJson(json); }
            catch (ArgumentException) { }
            catch (InvalidOperationException) { }
        }
    }

    private void Receive(object? sender, CoreWebView2WebMessageReceivedEventArgs args)
    {
        if (closed || args.Source != Origin + "index.html") return;
        var message = args.WebMessageAsJson;
        if (message.Length > 64_000) return;
        try
        {
            using var doc = JsonDocument.Parse(message);
            if (!doc.RootElement.TryGetProperty("action", out var action) || action.ValueKind != JsonValueKind.String) return;
            switch (action.GetString())
            {
                case "minimize": WindowState = FormWindowState.Minimized; return;
                case "close": Close(); return;
                case "ready": startupTimeout.Stop(); loading.Hide(); return;
                case "window":
                    Send(nativeDrag ? "{\"type\":\"window\",\"nativeDrag\":true}" : "{\"type\":\"window\",\"nativeDrag\":false}");
                    return;
                case "drag":
                    if (!nativeDrag)
                    {
                        ReleaseCapture();
                        SendMessageW(Handle, 0xA1, (IntPtr)2, IntPtr.Zero);
                    }
                    return;
            }
            if (worker is { HasExited: false }) worker.StandardInput.WriteLine(message);
        }
        catch (Exception error) when (error is JsonException or InvalidOperationException or IOException) { }
    }

    protected override void OnFormClosed(FormClosedEventArgs e)
    {
        closed = true;
        if (worker is { } process)
        {
            if (!process.HasExited)
            {
                try { process.Kill(entireProcessTree: true); }
                catch (InvalidOperationException) { }
            }
            process.Dispose();
        }
        base.OnFormClosed(e);
    }

    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);
        if (disposing)
        {
            startupTimeout.Dispose();
            appIcon?.Dispose();
        }
    }
}
