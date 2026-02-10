using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using FFGui.Models;

namespace FFGui.Services;

public abstract class FFmpegBaseParser
{
    protected readonly string _ffmpegPath;
    public delegate void ProgressCallback(string item, double progress);

    // Param: 1-4 spaces, must have a dash
    protected static readonly Regex ParamRegex = new(@"^\s{1,4}-?([\w:-]+)\s+<([^>]+)>\s+([EDVASFTR\.]{5,})\s*(.*)$", RegexOptions.Compiled);
    
    // Option: 3-20 spaces, must NOT have a dash at the start of the name group
    protected static readonly Regex OptionRegex = new(@"^\s{3,20}([\w_-]+)(?:\s+([-?\w\.]+))?\s+([EDVASFTR\.]{5,})\s*(.*)$", RegexOptions.Compiled);

    protected static readonly Regex SectionRegex = new(@"^([\w\s\(2\)]+)\s+AVOptions:$", RegexOptions.Compiled);

    private static readonly Dictionary<string, IFFmpegValue> NumericLimits = new(StringComparer.OrdinalIgnoreCase)
    {
        { "INT_MIN", new FFmpegValueLong(-2147483648) },
        { "INT_MAX", new FFmpegValueLong(2147483647) },
        { "UINT32_MAX", new FFmpegValueLong(4294967295) },
        { "I64_MIN", new FFmpegValueLong(-9223372036854775808) },
        { "I64_MAX", new FFmpegValueLong(9223372036854775807) },
        { "FLT_MAX", new FFmpegValueDouble(3.402823466e+38) },
        { "DBL_MAX", new FFmpegValueDouble(double.MaxValue) },
        { "auto", new FFmpegValueLong(-1) },
        { "none", new FFmpegValueLong(0) },
        { "disable", new FFmpegValueLong(0) },
        { "false", new FFmpegValueLong(0) },
        { "true", new FFmpegValueLong(1) }
    };

    protected FFmpegBaseParser(string ffmpegPath) => _ffmpegPath = ffmpegPath;

    protected Dictionary<string, FFmpegParameter> ParseAVOptions(string output)
    {
        var paramsDict = new Dictionary<string, FFmpegParameter>();
        string? currentParamKey = null;

        var lines = output.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);

        foreach (var line in lines)
        {
            if (SectionRegex.IsMatch(line)) continue;

            // Try Parameter Match (Starts with dash)
            var pMatch = ParamRegex.Match(line);
            if (pMatch.Success)
            {
                var name = pMatch.Groups[1].Value;
                var (clean, min, max, def) = CleanDescriptor(pMatch.Groups[4].Value);
                
                var param = new FFmpegParameter
                {
                    Type = pMatch.Groups[2].Value,
                    Description = clean,
                    Context = MapContext(pMatch.Groups[3].Value),
                    Min = min,
                    Max = max,
                    Default = def,
                    Options = new Dictionary<string, FFmpegOption>()
                };

                paramsDict[name] = param;
                currentParamKey = name;
                continue;
            }

            // Try Option Match (No dash, indented)
            var oMatch = OptionRegex.Match(line);
            if (oMatch.Success && currentParamKey != null)
            {
                //Console.WriteLine($"{currentParamKey}: {oMatch.Groups[1].Value} -> {oMatch.Groups[3].Value} -> {MapContext(oMatch.Groups[3].Value).ToYaml()}");
                // Extra safety: if it's a dash, it's a param that failed ParamRegex
                if (line.TrimStart().StartsWith("-")) continue;

                var optName = oMatch.Groups[1].Value;
                var optValStr = oMatch.Groups[2].Value;
                var optFlags = oMatch.Groups[3].Value;
                var optDescr = oMatch.Groups[4].Value;

                var option = new FFmpegOption
                {
                    Value = ToValue(string.IsNullOrEmpty(optValStr) ? optName : optValStr),
                    Description = optDescr.Trim(),
                    Context = MapContext(optFlags) 
                };

                var parent = paramsDict[currentParamKey];
                parent.Options ??= new Dictionary<string, FFmpegOption>();
                parent.Options[optName] = option;
                paramsDict[currentParamKey] = parent;
            }
        }
        return paramsDict;
    }

    protected IFFmpegValue? ToValue(string? val)
    {
        if (string.IsNullOrWhiteSpace(val)) return null;
        val = val.Trim();

        if (NumericLimits.TryGetValue(val, out var limit)) return limit;

        if (val.StartsWith("0x", StringComparison.OrdinalIgnoreCase))
        {
            if (long.TryParse(val.AsSpan(2), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out long hexVal))
                return new FFmpegValueLong(hexVal);
        }

        if (val.Contains('/'))
        {
            var parts = val.Split('/');
            if (parts.Length == 2 && 
                double.TryParse(parts[0], NumberStyles.Any, CultureInfo.InvariantCulture, out double n) && 
                double.TryParse(parts[1], NumberStyles.Any, CultureInfo.InvariantCulture, out double d))
                return new FFmpegValueDouble(d != 0 ? n / d : 0);
        }

        if (long.TryParse(val, NumberStyles.Integer, CultureInfo.InvariantCulture, out long l)) 
            return new FFmpegValueLong(l);
            
        if (double.TryParse(val, NumberStyles.Float | NumberStyles.AllowThousands, CultureInfo.InvariantCulture, out double dbl)) 
            return new FFmpegValueDouble(dbl);

        return new FFmpegValueString(val);
    }

    protected (string clean, IFFmpegValue? min, IFFmpegValue? max, IFFmpegValue? def) CleanDescriptor(string raw)
    {
        var minM = Regex.Match(raw, @"\(from\s+(-?[\w\./]+)");
        var maxM = Regex.Match(raw, @"to\s+(-?[\w\./]+)(?:\)|,)");
        var defM = Regex.Match(raw, @"default\s+(-?[\w\./]+)\)");

        string clean = Regex.Replace(raw, @"\(from.*?to.*?\)", "");
        clean = Regex.Replace(clean, @"\(default.*?\)", "");
        clean = Regex.Replace(clean.Trim(), @"^[EDVASFTR\.]{5,}\s+", "");

        IFFmpegValue? defValue = defM.Success
                ? ToValue(defM.Groups[1].Value)
                : new FFmpegValueString("");

        return (
            clean.Trim(),
            ToValue(minM.Groups[1].Value),
            ToValue(maxM.Groups[1].Value),
            defValue
        );
    }

    protected FFmpegContext MapContext(string f)
    {
        if (string.IsNullOrEmpty(f) || f.Length < 5) return new FFmpegContext();
        return new FFmpegContext
        {
            Encoding = f.Contains('E'),
            Decoding = f.Contains('D'),
            Filtering = f.Contains('F'),
            Video = f.Contains('V'),
            Audio = f.Contains('A'),
            Subtitle = f.Contains('S'),
            Timeline = f.Contains('T'),
            Runtime = f.Contains('R')
        };
    }

    protected async Task<string> RunCmdAsync(string args)
    {
        var psi = new ProcessStartInfo(_ffmpegPath, $"-hide_banner {args}")
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8
        };
        
        using var proc = Process.Start(psi);
        var outTask = proc!.StandardOutput.ReadToEndAsync();
        var errTask = proc!.StandardError.ReadToEndAsync();
        await Task.WhenAll(outTask, errTask);
        return string.IsNullOrEmpty(outTask.Result) ? errTask.Result : outTask.Result;
    }
}