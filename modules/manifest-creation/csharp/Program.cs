// Usage:
//   manifest-creation <input.txt> <provider> <company> [output.json]
//   manifest-creation --input <file.txt> --provider <name> --company <name> [--output <file.json>]
//
// When no output file is given, the output path is the input path with a .json extension.

using DWIS.API.DTO;

if (!CommandLineOptions.TryParse(args, out var options, out var error))
{
    if (error is not null)
    {
        Console.Error.WriteLine($"Error: {error}");
        Console.Error.WriteLine();
    }
    Console.Error.WriteLine(CommandLineOptions.Usage);
    return error is null ? 0 : 1;
}

Console.WriteLine($"Input file : {options.InputFile}");
Console.WriteLine($"Provider   : {options.Provider}");
Console.WriteLine($"Company    : {options.Company}");
Console.WriteLine($"Output file: {options.OutputFile}");

if (options != null)
{
    if (System.IO.File.Exists(options.InputFile))
    {
        string[] lines = System.IO.File.ReadAllLines(options.InputFile);
        if (lines != null && lines.Length > 0)
        {
            var voc = DWIS.Vocabulary.Standard.VocabularyProvider.GetDWISVocabulary();
            DWIS.Vocabulary.Development.DWISInstance dWISInstance = new("tool-kit", voc);
            if (DWIS.Vocabulary.Utils.VocabularyParsing.FromLines(lines, voc, dWISInstance))
            {
                ManifestFile manifest = ManifestFile.FromDWISInstance(dWISInstance, options.Provider, options.Company);
                if (manifest != null)
                {
                    var json = ManifestFile.ToJsonString(manifest);
                    System.IO.File.WriteAllText(options.OutputFile, json);  
                }
                else
                {
                    Console.Error.WriteLine("Error: Manifest generation failed");
                }
            }
            else
            {
                Console.Error.WriteLine("Error: Parsing failed");
            }
        }
        else
        {
            Console.Error.WriteLine("Error: Input file is empty.");
        }
    }
    else
    {
        Console.Error.WriteLine("Error: Input file does not exist.");
    }
}




return 0;

/// <summary>Command line options for the manifest creation tool.</summary>
public sealed record CommandLineOptions(string InputFile, string Provider, string Company, string OutputFile)
{
    public const string Usage = """
        Usage:
          manifest-creation <input.txt> <provider> <company> [output.json]
          manifest-creation --input <file.txt> --provider <name> --company <name> [--output <file.json>]

        Arguments:
          input      Path to the input .txt file (required).
          provider   Provider name (required).
          company    Company name (required).
          output     Path to the output .json file (optional).
                     Defaults to the input file path with a .json extension.

        Options:
          -h, --help Show this help text.
        """;

    /// <summary>
    /// Parses the command line. Returns false when the program should stop.
    /// In that case <paramref name="error"/> is null for a help request, or holds the problem otherwise.
    /// </summary>
    public static bool TryParse(string[] args, out CommandLineOptions options, out string? error)
    {
        options = null!;
        error = null;

        string? input = null, provider = null, company = null, output = null;
        var positional = new List<string>();

        for (var i = 0; i < args.Length; i++)
        {
            var arg = args[i];
            switch (arg)
            {
                case "-h":
                case "--help":
                case "/?":
                    return false;

                case "-i":
                case "--input":
                    if (!TryTakeValue(args, ref i, arg, out input, out error)) return false;
                    break;

                case "-p":
                case "--provider":
                    if (!TryTakeValue(args, ref i, arg, out provider, out error)) return false;
                    break;

                case "-c":
                case "--company":
                    if (!TryTakeValue(args, ref i, arg, out company, out error)) return false;
                    break;

                case "-o":
                case "--output":
                    if (!TryTakeValue(args, ref i, arg, out output, out error)) return false;
                    break;

                default:
                    if (arg.StartsWith('-'))
                    {
                        error = $"Unknown option '{arg}'.";
                        return false;
                    }
                    positional.Add(arg);
                    break;
            }
        }

        // Positional arguments fill whatever the named options did not set, in order.
        var queue = new Queue<string>(positional);
        input ??= queue.Count > 0 ? queue.Dequeue() : null;
        provider ??= queue.Count > 0 ? queue.Dequeue() : null;
        company ??= queue.Count > 0 ? queue.Dequeue() : null;
        output ??= queue.Count > 0 ? queue.Dequeue() : null;

        if (queue.Count > 0)
        {
            error = $"Too many arguments: '{string.Join("' '", queue)}'.";
            return false;
        }

        if (string.IsNullOrWhiteSpace(input))
        {
            error = "The input file path is required.";
            return false;
        }
        if (!string.Equals(Path.GetExtension(input), ".txt", StringComparison.OrdinalIgnoreCase))
        {
            error = $"The input file must be a .txt file: '{input}'.";
            return false;
        }
        if (!File.Exists(input))
        {
            error = $"The input file was not found: '{input}'.";
            return false;
        }
        if (string.IsNullOrWhiteSpace(provider))
        {
            error = "The provider name is required.";
            return false;
        }
        if (string.IsNullOrWhiteSpace(company))
        {
            error = "The company name is required.";
            return false;
        }

        input = Path.GetFullPath(input);
        output = string.IsNullOrWhiteSpace(output)
            ? Path.ChangeExtension(input, ".json")
            : Path.GetFullPath(output);

        options = new CommandLineOptions(input, provider.Trim(), company.Trim(), output);
        return true;
    }

    private static bool TryTakeValue(string[] args, ref int i, string option, out string? value, out string? error)
    {
        value = null;
        error = null;
        if (i + 1 >= args.Length || args[i + 1].StartsWith('-'))
        {
            error = $"Option '{option}' requires a value.";
            return false;
        }
        value = args[++i];
        return true;
    }
}
