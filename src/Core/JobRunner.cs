namespace FFGui.Core;

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using FFGui.Helpers;
using FFGui.Models;
using FFGui.Services;

public class JobRunner
{
    private readonly List<Process> _activeProcesses = new();
    private readonly object _lock = new();
    private bool _isStopping = false;
    private CancellationTokenSource? _cts;

    private readonly FFGuiApp _app;
    public bool IsRunning { get; private set; }

    // Events to notify the UI
    public event Action? OnQueueStarted;
    public event Action<int, Job>? OnJobStarted;
    public event Action<int, Job, string, double>? OnJobProgressUpdated;
    public event Action<int, Job>? OnJobFinished;
    public event Action<double>? OnTotalProgressChanged;
    public event Action? OnQueueFinished;

    public JobRunner(FFGuiApp app)
    {
        _app = app;
    }

    public async Task RunQueueAsync(bool retryFailedOnly = false)
    {
        if (IsRunning || _app.Jobs == null || _app.Jobs.Count == 0) return;

        _isStopping = false;
        IsRunning = true;
        _cts?.Dispose();
        _cts = new CancellationTokenSource();

        OnQueueStarted?.Invoke();

        // Filter jobs to run
        var jobsToRun = _app.Jobs
            .Where(kv => !retryFailedOnly || kv.Value.Status == Job.JobStatus.Failed)
            .ToList();

        if (jobsToRun.Count == 0)
        {
            IsRunning = false;
            OnQueueFinished?.Invoke();
            return;
        }

        // Organize by Parallel Groups
        // Group 0 = Sequential (Each job is its own batch)
        // Group > 0 = Parallel (All jobs in that group run at once)
        var sequentialJobs = jobsToRun.Where(j => j.Value.ParallelGroup == 0).OrderBy(j => j.Key);
        var parallelGroups = jobsToRun.Where(j => j.Value.ParallelGroup > 0)
                                      .GroupBy(j => j.Value.ParallelGroup)
                                      .OrderBy(g => g.Key);

        int completedCount = 0;
        int totalJobs = jobsToRun.Count;

        // Process Parallel Groups first (Order by ParallelGroup number)
        foreach (var group in parallelGroups)
        {
            if (_isStopping || _cts.Token.IsCancellationRequested) break;
            var tasks = group.Select(kv => ExecuteJobAsync(kv.Key, kv.Value, _cts.Token)).ToList();
            await Task.WhenAll(tasks);
            completedCount += tasks.Count;
            OnTotalProgressChanged?.Invoke((double)completedCount / totalJobs);
        }

        // Process Sequential Jobs (Group 0)
        foreach (var (id, job) in sequentialJobs)
        {
            if (_isStopping || _cts.Token.IsCancellationRequested) break;
            await ExecuteJobAsync(id, job, _cts.Token);
            completedCount++;
            OnTotalProgressChanged?.Invoke((double)completedCount / totalJobs);
        }

        OnTotalProgressChanged?.Invoke(1.0);
        IsRunning = false;
        OnQueueFinished?.Invoke();
    }

    private async Task ExecuteJobAsync(int id, Job job, CancellationToken token)
    {
        if (token.IsCancellationRequested) return;
        job.Status = Job.JobStatus.Running;
        OnJobStarted?.Invoke(id, job);

        // Build command with progress reporting redirected to stdout
        var args = job.CompileFFmpegCmd(_app.Cache).ToList();
        args.Add("-progress");
        args.Add("pipe:1");
        args.Add("-nostats"); // Disable standard noisy stats to make parsing pipe:1 cleaner

        string quotedCommand = $"{_app.FFMpegPath} " + string.Join(" ", args.Select(a => $"\"{a}\""));
        Console.WriteLine($"\n[JobRunner] Job {id}: '{job.Name}' Executing Command:\n{quotedCommand}\n");

        var startInfo = new ProcessStartInfo
        {
            FileName = _app.FFMpegPath,
            Arguments = string.Join(" ", args.Select(a => $"\"{a}\"")),
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true
        };
        var localProgressBuffer = new Dictionary<string, string>();

        using var process = new Process { StartInfo = startInfo };

        var errorLog = new System.Text.StringBuilder();
        process.ErrorDataReceived += (s, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
            {
                errorLog.AppendLine(e.Data);
                Console.WriteLine($"[FFmpeg Log] {e.Data}");
            }
        };

        // Calculation of the actual expected output duration
        double effectiveJobDuration = 0;
        foreach (var source in job.Sources)
        {
            foreach (var stream in source.Streams.Where(s => s.Active))
            {
                double streamDur = CalculateEffectiveDuration(stream.Duration, stream.Trim);
                if (streamDur > effectiveJobDuration)
                    effectiveJobDuration = streamDur;
            }
        }

        // Fallback to original if trim logic results in 0
        if (effectiveJobDuration <= 0) effectiveJobDuration = job.TotalDuration;

        // Use THIS duration for your progress parsing
        process.OutputDataReceived += (s, e) =>
        {
            if (string.IsNullOrEmpty(e.Data)) return;
            ParseProgress(id, job, e.Data, effectiveJobDuration, localProgressBuffer);
        };

        try
        {
            process.Start();

            lock (_lock)
            {
                _activeProcesses.Add(process);
            }

            process.BeginOutputReadLine();
            process.BeginErrorReadLine(); // We read error to keep the buffer clean, though we parse stdout

            await process.WaitForExitAsync();

            job.Status = process.ExitCode == 0 ? Job.JobStatus.Successful : Job.JobStatus.Failed;
            job.ErrorLog = errorLog.ToString();
        }
        catch (OperationCanceledException)
        {
            job.Status = Job.JobStatus.Pending; // User stopped the queue
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Process Error: {ex.Message}");
            job.Status = Job.JobStatus.Failed;
        }
        finally
        {
            // REMOVE FROM LIST: Make sure we clean up so Stop() doesn't try to close dead processes
            lock (_lock) { _activeProcesses.Remove(process); }
            OnJobFinished?.Invoke(id, job);
            await Task.Delay(200);
        }

        OnJobFinished?.Invoke(id, job);
    }

    public void Stop(bool force = false)
    {
        _isStopping = true;
        _cts?.Cancel();
        lock (_lock)
        {
            foreach (var p in _activeProcesses)
            {
                if (force)
                {
                    p.Kill(true);
                }
                else
                {
                    // STRATEGY: 
                    // 1. Try to tell FFmpeg to stop via its own 'q' command first
                    // 2. Close the pipe to trigger EOF
                    // 3. Wait 2 seconds, if it hasn't died, then kill it.

                    Task.Run(async () =>
                    {
                        try
                        {
                            await p.StandardInput.WriteLineAsync("q");
                            p.StandardInput.Close();

                            // Give FFmpeg 2 seconds to write the header/trailer
                            using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(120));
                            await p.WaitForExitAsync(cts.Token);
                        }
                        catch
                        {
                            // If it's still alive after 120 seconds or crashes during stop
                            if (!p.HasExited) p.Kill();
                        }
                    });
                }
            }
        }
    }

    // Helper for machine-readable progress parsing (-progress pipe:1)
    private Dictionary<string, string> _progressBuffer = new();
    private void ParseProgress(int id, Job job, string line, double totalDuration, Dictionary<string, string> buffer)
    {
        var parts = line.Split('=', 2);
        if (parts.Length < 2) return;

        string key = parts[0].Trim();
        string val = parts[1].Trim();
        buffer[key] = val;

        // FFmpeg sends "progress=continue" or "progress=end" to signal a block update
        if (key == "progress")
        {
            if (buffer.TryGetValue("out_time_ms", out var timeStr) && long.TryParse(timeStr, out long us))
            {
                double currentSec = us / 1000000.0;
                double pct = Math.Clamp(currentSec / totalDuration, 0.0, 1.0);

                string speed = buffer.GetValueOrDefault("speed", "0x");
                string fps = buffer.GetValueOrDefault("fps", "0");
                string bitrate = buffer.GetValueOrDefault("bitrate", "0");
                // --- ETA CALCULATION ---
                string eta = "Calculating...";

                // FFmpeg speed is like "1.23x". We strip the 'x' to parse it as a double.
                string cleanSpeed = speed.Replace("x", "").Trim();
                string speedFormatted = "";
                if (double.TryParse(cleanSpeed, CultureInfo.InvariantCulture, out double velocity) && velocity > 0.01)
                {
                    // Formula: (Remaining Media Seconds) / Speed Multiplier
                    double remainingMediaSec = Math.Max(0, totalDuration - currentSec);
                    double remainingRealSec = remainingMediaSec / velocity;

                    eta = FormatEta(remainingRealSec);
                    speedFormatted = $"{Math.Round(velocity, 2):0.00}x  ";
                }

                string info = $"{Math.Round(pct * 100, 2):0.00}%  {bitrate}  {fps} fps  {speedFormatted}{eta} left";

                OnJobProgressUpdated?.Invoke(id, job, info, pct);
            }
        }
    }

    public static double CalculateEffectiveDuration(double originalDuration, Job.Source.Stream.TrimSettings trim)
    {
        double start = 0;
        double duration = originalDuration;

        // Parse Start
        if (FFmpegTimeParser.TryParse(trim.Start, out var tsStart))
            start = tsStart.TotalSeconds;

        // If Length (-t) is provided, it overrides everything
        if (FFmpegTimeParser.TryParse(trim.Length, out var tsLen))
        {
            return tsLen.TotalSeconds;
        }

        // If End (-to) is provided, duration is End - Start
        if (FFmpegTimeParser.TryParse(trim.End, out var tsEnd))
        {
            return Math.Max(0, tsEnd.TotalSeconds - start);
        }

        // Otherwise, it's just Original - Start
        return Math.Max(0, originalDuration - start);
    }

    private static string FormatEta(double totalSeconds)
    {
        if (double.IsInfinity(totalSeconds) || double.IsNaN(totalSeconds) || totalSeconds < 0) 
            return "Unknown";

        TimeSpan t = TimeSpan.FromSeconds(totalSeconds);

        // More than 24 hours
        if (t.TotalHours >= 24)
        {
            return $"{(int)t.TotalDays} days, {t.Hours} hours";
        }
        
        // Less than 24h but more than 59m
        if (t.TotalHours >= 1)
        {
            return $"{t.Hours} hours, {t.Minutes} min, {t.Seconds} sec";
        }

        // Less than an hour but more than 59s
        if (t.TotalMinutes >= 1)
        {
            return $"{t.Minutes} minutes {t.Seconds} seconds";
        }

        // Less than a minute
        return $"< 1 min ({t.Seconds} seconds)";
    }
}