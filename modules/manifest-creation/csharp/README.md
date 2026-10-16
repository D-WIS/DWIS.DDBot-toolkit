# C# manifest creation

Original .NET 8 console implementation. Dependencies are pinned in
`manifest-creation.csproj`: `DWIS.API.DTO` 2.2.32 and `DWIS.Vocabulary.Standard` /
`DWIS.Vocabulary.Utils` 1.0.172.

From the repository root:

```bash
dotnet build modules/manifest-creation/csharp/manifest-creation.csproj
dotnet run --project modules/manifest-creation/csharp/manifest-creation.csproj -- input.txt Provider Company output.json
```

Building requires the .NET 8 SDK and access to NuGet on the initial restore. `bin/` and
`obj/` are generated output and are excluded from version control. The `.slnx` file is
retained for IDEs/SDKs that support that solution format; the commands above target the
project directly.

The CLI accepts positional or named input/provider/company/output arguments. Without an
output argument, it uses the input path with a `.json` extension.

The entry point currently uses the upstream parser's Markdown default and leaves the
instance collections uninitialized. Consequently ordinary CONFIG lines can be ignored,
and recognized declarations can fail. See the
[Python implementation's compatibility notes](../python/README.md#intentional-input-handling-fixes)
for the verified behavior and fixes provided by that implementation.

The module-level [README](../README.md) describes the shared contract and tests.
