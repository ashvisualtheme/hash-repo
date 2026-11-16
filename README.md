# <p align="center">Official Hash Baseline Repository<br>for the File Integrity Scanner Plugin</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/ashvisualtheme/hash-repo/main/asset/sha256-cert.png" alt="Header Image" width="150"/>
</p>

<p align="center">
 <strong>Powering the<br>🛡️ <a href="https://github.com/ashvisualtheme/file-integrity-scanner">File Integrity Scanner Plugin for PKP Platform (OJS/OMP/OPS)</a></strong>
</p>

<p align="center">
    <a href="https://github.com/ashvisualtheme/hash-repo/actions/workflows/generate-core-hash.yml">
        <img src="https://github.com/ashvisualtheme/hash-repo/actions/workflows/generate-core-hash.yml/badge.svg" alt="Automatic Generate Hash for OJS/OMP/OPS Core">
    </a>
    <a href="https://github.com/ashvisualtheme/hash-repo/actions/workflows/generate-plugins-hash.yml">
        <img src="https://github.com/ashvisualtheme/hash-repo/actions/workflows/generate-plugins-hash.yml/badge.svg" alt="Automatic Generate Hash for OJS/OMP/OPS Plugins">
    </a>
    <a href="https://github.com/ashvisualtheme/hash-repo/actions/workflows/generate-plugin-gallery-hashes.yml">
        <img src="https://github.com/ashvisualtheme/hash-repo/actions/workflows/generate-plugin-gallery-hashes.yml/badge.svg" alt="Batch Generate Hashes from the PKP Plugin Gallery">
    </a>
</p>

This repository contains the official, version-specific **SHA-256 checksums** for PKP Platform (OJS/OMP/OPS) core, plugin, and theme files. It serves as the trusted, centralized baseline that our File Integrity Scanner plugin uses to detect unauthorized modifications and ensure the security of your journal's installation.

---

## The Role of This Repository

The **File Integrity Scanner Plugin** strengthens your OJS security by proactively scanning your application files and comparing them against the cryptographic hashes stored here. This repository is the source of truth for what your files *should* look like.

When the plugin runs its daily scan, it fetches the relevant baseline files from this repository to perform its comparison. Any deviation—whether a file is **Modified**, **Added**, or **Deleted**—is immediately flagged and reported to the site administrator.

➡️ **To learn more or download the main plugin, visit the [File Integrity Scanner Plugin Repository](https://github.com/ashvisualtheme/file-integrity-scanner).**

---

## Contributing to the Hash Ecosystem

We encourage OJS/OMP/OPS plugin and theme developers to contribute to this security ecosystem. By adding hash baselines for your public projects, you enable thousands of PKP OJS/OMP/OPS administrators to verify the integrity of your software automatically.

### How to Add Your Hashes

Our system uses a GitHub Actions workflow to automate the generation of correctly formatted SHA-256 hash files.

To generate and contribute hashes for a new plugin or theme version, please follow these steps:

1.  Navigate to the **Actions** tab of this repository.
2.  Select the **Generate Hash with Manual Input** workflow.
3.  Click the **Run workflow** button.
4.  Provide the required inputs:
    * **Full URL of the .tar.gz file to process**: The complete, public URL of the release archive you want to process.
    * **Plugin category for the folder structure**: The category of the plugin (e.g., `themes`, `blocks`, `generic`) to ensure the hash file is placed in the correct directory.
5.  Click **Run workflow** to start the process.

Once the workflow is complete, a new JSON hash file will be available as a downloadable artifact. Please create a pull request to add this file to the repository.

### Batch Generation from the Plugin Gallery

The **Generate Plugin Gallery Hashes** workflow builds the same baselines from the
[PKP Plugin Gallery](https://github.com/pkp/plugin-gallery) feed
(`plugins.xml`) instead of taking a single URL by hand. It is the faster route
when you want the whole catalogue, or every release of one plugin.

1.  Navigate to the **Actions** tab and select **Generate Plugin Gallery Hashes**.
2.  Click **Run workflow**.
3.  Choose the inputs:
    * **Application platform**: `ojs2`, `omp`, or `ops`.
    * **Category**, **Product**, **Version**: optional filters. Leave them empty to process the whole catalogue.
    * **Batch size**: how many releases each parallel job handles (default 40).
    * **Overwrite**: rewrite baselines that already exist. Off by default, so existing files are left untouched.
    * **Create pull request**: open a pull request with the results (on by default).
4.  Click **Run workflow**.

Each release is downloaded, verified against the MD5 published in the gallery
feed, extracted, and hashed file by file. Releases are spread over parallel
batches, so the full OJS catalogue completes in a few minutes rather than the
hours a single manual run would take.

The workflow reports releases whose tarball is no longer downloadable in the run
summary. Three `funding` releases are currently affected because the upstream
release assets have been removed.

#### File naming

The scanner asks for a baseline by file name, and it derives that name from the
plugin's own `version.xml`. The gallery feed and the plugin's `version.xml` do
not always agree, so a release is written under every name that could be
requested:

* the gallery version, for example `gopher-1.0.0.1.json`;
* the raw `version.xml` release, for example `adminNotificationManager-1.4.0-0.json`;
* the normalised four-part version PKP computes at runtime, for example `rqc-1.0.0.0.json`.

Where two releases of the same plugin claim the same name, the highest version
owns the file and the collision is reported in the workflow summary.

#### Running the scripts directly

The two helper scripts under `tools/` can also be run on their own:

```bash
# Resolve the gallery feed into a manifest of releases
python3 tools/build_manifest.py --plugins-xml plugins.xml --output manifest.jsonl --application ojs2

# Download and hash the releases listed in the manifest
python3 tools/generate_hashes.py --manifest manifest.jsonl --output-dir ojs/plugins --jobs 8
```

`build_manifest.py` needs network access, because it reads each release's
`version.xml` to work out the runtime file names. `generate_hashes.py` can
reuse that manifest without touching the network beyond the downloads
themselves.

---

## Development and Support

### Developed and Maintained by [**AshVisualTheme**](https://ashvisual.com/)
This repository and the associated File Integrity Scanner plugin are developed and maintained by AshVisualTheme. We are committed to supporting the security of the OJS community.

📧 **Dedicated Support:** For technical support or inquiries regarding custom OJS development, please contact us at `support@ashvisual.com`.

### 🎨 Transform Your Journal: Discover Professional OJS Themes
As specialists in OJS infrastructure, **AshVisualTheme** also develops high-quality, professional themes.

Stop using default OJS templates. **Elevate your reader and author experience today!**

➡️ **View Our Professional Themes in Action:** <https://demo-ojs.ashvisual.com>

---

## License

The hash files in this repository are provided for public use. The scripts and workflows are released under the **GNU General Public License v3**. See the `LICENSE` file for full terms.
