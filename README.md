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
