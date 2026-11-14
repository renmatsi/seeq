internal sealed class StartupPrompt : Control
{
    private readonly List<string> commands = ["seeq.boot()"];
    private readonly System.Windows.Forms.Timer cursor = new() { Interval = 180 };
    private readonly Font title = new("Consolas", 19f, FontStyle.Bold);
    private readonly Font code = new("Consolas", 12f);
    private int frame;

    internal StartupPrompt()
    {
        Dock = DockStyle.Fill;
        BackColor = Color.FromArgb(7, 8, 10);
        ForeColor = Color.FromArgb(230, 233, 240);
        DoubleBuffered = true;
        AccessibleName = "Inicialização do seeq";
        AccessibleRole = AccessibleRole.StaticText;
        cursor.Tick += (_, _) => { frame = (frame + 1) % 4; Invalidate(); };
    }

    internal void Step(string command)
    {
        commands.Add(command);
        AccessibleDescription = command;
        Invalidate();
    }

    protected override void OnVisibleChanged(EventArgs e)
    {
        base.OnVisibleChanged(e);
        cursor.Enabled = Visible && SystemInformation.IsMenuAnimationEnabled;
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        int Scale(int value) => value * DeviceDpi / 96;
        const TextFormatFlags flags = TextFormatFlags.NoPadding | TextFormatFlags.NoPrefix;
        var x = Math.Max(Scale(32), (Width - Scale(430)) / 2);
        var y = Math.Max(Scale(24), (Height - Scale(210)) / 2);
        TextRenderer.DrawText(e.Graphics, "seeq", title, new Point(x, y), ForeColor, flags);
        y += Scale(47);
        for (int i = 0; i < commands.Count; i++)
        {
            bool active = i == commands.Count - 1;
            string marker = active ? "> " : "  ";
            string suffix = active ? $"  {"|/-\\"[frame]}" : "  [ok]";
            var color = active ? Color.FromArgb(113, 163, 255) : Color.FromArgb(136, 146, 163);
            TextRenderer.DrawText(e.Graphics, marker + commands[i] + suffix, code, new Point(x, y), color, flags);
            y += Scale(26);
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            cursor.Dispose();
            title.Dispose();
            code.Dispose();
        }
        base.Dispose(disposing);
    }
}
