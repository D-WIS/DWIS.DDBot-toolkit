// Reference harness for the manifest-creation module.
//
// It sits outside the module, does not reference the C# implementation source, and is never
// shipped: it pins the same NuGet packages and exposes the DWIS library conversion path exactly
// as modules/manifest-creation/README.md describes, so the Python implementation can be compared
// against the pinned libraries:
//
//   manifest <input.txt> <provider> <company> <output.json>
//       new DWISInstance("tool-kit", vocabulary) with initialized collections,
//       VocabularyParsing.FromLines(lines, vocabulary, instance, fromMD: false),
//       ManifestFile.FromDWISInstance(...), ManifestFile.ToJsonString(...).
//
//   vocabulary <output.json>
//       Projects VocabularyProvider.GetDWISVocabulary() into the same shape as the bundled
//       Python vocabulary snapshot, retaining every field the converter reads.
//
// Exit codes: 0 success, 1 conversion or parsing failure, 2 usage/IO error.

using System.Text.Encodings.Web;
using System.Text.Json;
using DWIS.API.DTO;
using DWIS.Vocabulary.Development;

const string Usage = """
    Usage:
      reference-harness manifest <input.txt> <provider> <company> <output.json>
      reference-harness vocabulary <output.json>
    """;

static int Fail(string message)
{
    Console.Error.WriteLine($"Error: {message}");
    return 2;
}

static int ParseProblem(string message)
{
    Console.Error.WriteLine($"Error: {message}");
    return 1;
}

static DWISInstance NewInstance(DWISVocabulary vocabulary) => new("tool-kit", vocabulary)
{
    Population = new SimplePopulation(),
    Sentences = new SimpleSentenceCollection(),
    ClassAssertions = new SimpleClassAssertionCollection(),
    ImplicitSentences = new SimpleImplicitSentenceCollection(),
};

static void WriteJson(string path, object value)
{
    var options = new JsonSerializerOptions
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };
    System.IO.File.WriteAllText(path, JsonSerializer.Serialize(value, options) + "\n");
}

if (args.Length == 0)
{
    Console.Error.WriteLine(Usage);
    return 2;
}

switch (args[0])
{
    case "manifest":
    {
        if (args.Length != 5)
        {
            return Fail("manifest requires <input.txt> <provider> <company> <output.json>.");
        }

        string input = args[1], provider = args[2], company = args[3], output = args[4];
        if (!System.IO.File.Exists(input))
        {
            return Fail($"Input file not found: '{input}'.");
        }

        string[] lines = System.IO.File.ReadAllLines(input);
        if (lines.Length == 0)
        {
            return ParseProblem("Input file is empty.");
        }

        var vocabulary = DWIS.Vocabulary.Standard.VocabularyProvider.GetDWISVocabulary();
        var instance = NewInstance(vocabulary);
        bool parsed;
        try
        {
            parsed = DWIS.Vocabulary.Utils.VocabularyParsing.FromLines(lines, vocabulary, instance, false);
        }
        catch (Exception exception)
        {
            return ParseProblem($"Parsing threw {exception.GetType().Name}: {exception.Message}");
        }

        if (!parsed)
        {
            return ParseProblem("Parsing failed.");
        }

        ManifestFile? manifest = ManifestFile.FromDWISInstance(instance, provider, company);
        if (manifest is null)
        {
            return ParseProblem("Manifest generation failed.");
        }

        System.IO.File.WriteAllText(output, ManifestFile.ToJsonString(manifest));
        return 0;
    }

    case "vocabulary":
    {
        if (args.Length != 2)
        {
            return Fail("vocabulary requires <output.json>.");
        }

        var vocabulary = DWIS.Vocabulary.Standard.VocabularyProvider.GetDWISVocabulary();
        var nouns = new Dictionary<string, object?>();
        foreach (Noun noun in vocabulary.Nouns)
        {
            nouns[noun.Name] = new Dictionary<string, object?>
            {
                ["Name"] = noun.Name,
                ["ParentNounName"] = noun.ParentNounName,
                ["NounAttributes"] = noun.NounAttributes is null or { Length: 0 }
                    ? null
                    : noun.NounAttributes.Select(attribute => new Dictionary<string, object?>
                    {
                        ["Type"] = attribute.Type,
                        ["Name"] = attribute.Name,
                        ["DisplayName"] = attribute.DisplayName,
                        ["Description"] = attribute.Description,
                    }).ToArray(),
            };
        }

        WriteJson(args[1], new Dictionary<string, object?>
        {
            ["Nouns"] = nouns,
            ["Verbs"] = vocabulary.Verbs.Select(verb => verb.Name).ToArray(),
        });
        return 0;
    }

    default:
        return Fail($"Unknown command '{args[0]}'.\n{Usage}");
}