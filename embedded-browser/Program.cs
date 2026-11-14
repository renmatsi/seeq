using System.Reflection;
using System.Text;
using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        string? fixture = null;
#if DEBUG
        if (args.Length >= 4 && args[0] == "--fixture")
        {
            fixture = Path.GetFullPath(args[1]);
            args = args[2..];
        }
#endif
        var automatic = args.Length == 3 && args[0] == "--auto";
        if (automatic) args = args[1..];
        if (args.Length != 2 || !Uri.TryCreate(args[0], UriKind.Absolute, out var target)
            || !BrowserWindow.IsAllowed(target, target.IdnHost))
            return 2;

        ApplicationConfiguration.Initialize();
        using var window = new BrowserWindow(target, Path.GetFullPath(args[1]), fixture, automatic);
        Application.Run(window);
        if (window.Result is not null)
        {
            using var output = new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false));
            output.Write(window.Result);
        }
        return window.ExitCode;
    }
}

internal sealed class BrowserWindow : Form
{
    private readonly Uri target;
    private readonly string profile;
    private readonly string? fixture;
    private readonly string host;
    private readonly bool automatic;
    private readonly System.Windows.Forms.Timer watch = new() { Interval = 600 };
    private readonly WebView2 web = new() { Dock = DockStyle.Fill };
    private readonly Button import = new() { Text = "Importar para o seeq", AutoSize = true, Enabled = false };
    private readonly Label hint = new() { Text = "Abrindo a página…", Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft };
    private bool closing;
    private bool needsInteraction;
    private bool ready;
    private bool capturing;
    private long deadline;
    internal string? Result { get; private set; }
    internal int ExitCode { get; private set; }

    internal BrowserWindow(Uri target, string profile, string? fixture, bool automatic)
    {
        this.target = target;
        this.profile = profile;
        this.fixture = fixture;
        this.automatic = automatic;
        host = target.IdnHost;
        Text = $"seeq — {host}";
        StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(1120, 740);
        MinimumSize = new Size(660, 420);
        if (automatic)
        {
            Opacity = 0;
            ShowInTaskbar = false;
            deadline = Environment.TickCount64 + 25_000;
            watch.Tick += WatchAsync;
        }

        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 2 };
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 52));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        var toolbar = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 4, Padding = new Padding(8) };
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        var reload = new Button { Text = "Recarregar", AutoSize = true, Enabled = false };
        reload.Click += (_, _) => web.CoreWebView2?.Reload();
        var back = new Button { Text = "Voltar", AutoSize = true, Enabled = false };
        back.Click += (_, _) => { if (web.CanGoBack) web.GoBack(); };
        toolbar.Controls.Add(import, 0, 0);
        toolbar.Controls.Add(reload, 1, 0);
        toolbar.Controls.Add(back, 2, 0);
        toolbar.Controls.Add(hint, 3, 0);
        layout.Controls.Add(toolbar, 0, 0);
        layout.Controls.Add(web, 0, 1);
        Controls.Add(layout);
        import.Click += async (_, _) => await CaptureAsync();
        FormClosing += (_, _) =>
        {
            closing = true;
            watch.Stop();
        };
        FormClosed += (_, _) => watch.Dispose();
        Shown += async (_, _) =>
        {
            if (automatic) watch.Start();
            await InitializeAsync(reload, back);
        };
    }

    protected override bool ShowWithoutActivation => automatic && !needsInteraction;

    internal static bool IsAllowed(Uri uri, string originHost)
    {
        static string Bare(string name) => name.StartsWith("www.", StringComparison.Ordinal) ? name[4..] : name;
        var host = Bare(uri.IdnHost);
        return uri.Scheme == Uri.UriSchemeHttps && uri.IsDefaultPort && uri.UserInfo.Length == 0
            && host is "ext.to" or "1337x.to" && host == Bare(originHost);
    }

    private async Task InitializeAsync(Button reload, Button back)
    {
        try
        {
            var environment = await CoreWebView2Environment.CreateAsync(userDataFolder: profile);
            if (closing) return;
            await web.EnsureCoreWebView2Async(environment);
            if (closing) return;
            var browser = web.CoreWebView2;
            browser.Settings.IsWebMessageEnabled = false;
            browser.Settings.AreDevToolsEnabled = false;
            browser.NavigationStarting += (_, e) =>
            {
                if (!Uri.TryCreate(e.Uri, UriKind.Absolute, out var address) || !IsAllowed(address, host))
                {
                    e.Cancel = true;
                    return;
                }
                ready = false;
                import.Enabled = false;
            };
            browser.NewWindowRequested += (_, e) => e.Handled = true;
            browser.DownloadStarting += (_, e) => e.Cancel = true;
            browser.PermissionRequested += (_, e) => e.State = CoreWebView2PermissionState.Deny;
            browser.HistoryChanged += (_, _) => back.Enabled = browser.CanGoBack;
            browser.NavigationCompleted += async (_, e) =>
            {
                if (closing) return;
                if (automatic && e.HttpStatusCode == 429)
                {
                    ExitCode = 6;
                    Close();
                    return;
                }
                if (automatic && e.HttpStatusCode == 403)
                    Reveal();
                ready = e.IsSuccess && e.HttpStatusCode != 403;
                import.Enabled = true;
                if (!needsInteraction)
                    hint.Text = e.IsSuccess || e.HttpStatusCode == 403
                        ? "Clique em Importar quando a página carregar. Se houver verificação, siga as instruções do site."
                        : "A página não carregou por completo. Você pode tentar recarregar.";
#if DEBUG
                if (fixture is not null && !automatic)
                    await CaptureAsync();
#else
                await Task.CompletedTask;
#endif
            };
#if DEBUG
            if (fixture is not null)
                browser.SetVirtualHostNameToFolderMapping(host, fixture, CoreWebView2HostResourceAccessKind.Deny);
#endif
            reload.Enabled = true;
            browser.Navigate(target.AbsoluteUri);
        }
        catch (Exception)
        {
            if (closing) return;
            ExitCode = 3;
            Close();
        }
    }

    private void Reveal()
    {
        if (needsInteraction || closing) return;
        needsInteraction = true;
        deadline = Environment.TickCount64 + 120_000;
        ShowInTaskbar = true;
        Opacity = 1;
        Activate();
        hint.Text = "O site pede verificação. Siga as instruções da página. A busca continua quando a lista carregar.";
#if DEBUG
        if (fixture is not null)
            Console.Error.WriteLine("fixture: interaction shown");
#endif
    }

    private async void WatchAsync(object? sender, EventArgs e)
    {
        if (closing) return;
        if (Environment.TickCount64 >= deadline)
        {
            ExitCode = needsInteraction ? 7 : 5;
            Close();
            return;
        }
        if (ready)
            await CaptureAsync();
    }

    private async Task CaptureAsync()
    {
        if (capturing || web.Source is not Uri address || !IsAllowed(address, host))
            return;
        capturing = true;
        import.Enabled = false;
        try
        {
            using var resource = Assembly.GetExecutingAssembly().GetManifestResourceStream("collect.js")!;
            using var reader = new StreamReader(resource);
            var value = await web.CoreWebView2.ExecuteScriptAsync(await reader.ReadToEndAsync());
            if (closing) return;
            using var data = JsonDocument.Parse(value);
            if (data.RootElement.ValueKind != JsonValueKind.Object)
                hint.Text = "Aguarde a página carregar e tente de novo.";
            else if (data.RootElement.TryGetProperty("error", out var error))
            {
                if (automatic && data.RootElement.TryGetProperty("challenge", out var challenge)
                    && challenge.ValueKind == JsonValueKind.True)
                    Reveal();
                else if (!automatic)
                    hint.Text = error.GetString();
            }
            else if (data.RootElement.TryGetProperty("format", out var format)
                && format.GetString() == "torrentfindr-page-v1" && value.Length <= 500_000)
            {
                Result = value;
                Close();
            }
        }
        catch (Exception)
        {
            if (!closing) hint.Text = "Não consegui ler a página. Recarregue e tente novamente.";
        }
        finally
        {
            capturing = false;
            if (!closing) import.Enabled = true;
#if DEBUG
            if (fixture is not null && !automatic && Result is null && !closing)
            {
                ExitCode = 4;
                Close();
            }
#endif
        }
    }
}
