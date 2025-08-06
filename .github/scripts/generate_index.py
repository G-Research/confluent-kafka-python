import os
import sys
import re
import itertools
import requests
import hashlib

from urllib.parse import quote
from pathlib import Path
from github import Github
from typing import List, Dict, Set

# Define yanked versions - modify this dictionary as needed
yanked_versions = {
         "confluent-kafka": {
             "2.11.0+gr",
             "2.11.0+gr.1",
         },
    }

HTML_TEMPLATE = """<!DOCTYPE html>
 <html>
 <head>
     <title>{package_name}</title>
 </head>
 <body>
     <h1>{package_name}</h1>
     {package_links}
 </body>
 </html>
"""

def normalize(name):
    """Normalize package name according to PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()

def calculate_sha256(file_path):
    with open(file_path, "rb") as f:
        digest = hashlib.file_digest(f, "sha256")

    return digest.hexdigest()

def extract_version_from_filename(filename: str) -> str:
    """Extract version from wheel or sdist filename."""
    # Remove extension
    name = filename.replace('.tar.gz', '').replace('.whl', '')
    
    # For wheels: package-version-python-abi-platform
    # For sdist: package-version
    parts = name.split('-')
    if len(parts) >= 2:
        return parts[1]
    return ""

class PackageIndexBuilder:
    def __init__(self, token: str, repo_name: str, output_dir: str, yanked_versions: Dict[str, Set[str]] = None):
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        self.output_dir = Path(output_dir)
        self.packages: Dict[str, List[Dict]] = {}
        self.yanked_versions = yanked_versions or {}
        
        # Set up authenticated session
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/octet-stream",
        })

    def is_version_yanked(self, package_name: str, version: str) -> bool:
        """Check if a specific version of a package is yanked."""
        normalized_package = normalize(package_name)
        return normalized_package in self.yanked_versions and version in self.yanked_versions[normalized_package]

    def collect_packages(self):
        print("Query release assets")
        
        for release in self.repo.get_releases():
            for asset in release.get_assets():
                if asset.name.endswith(('.whl', '.tar.gz')):
                    package_name = normalize(asset.name.split('-')[0])
                    if package_name not in self.packages:
                        self.packages[package_name] = []

                    version = extract_version_from_filename(asset.name)
                    self.packages[package_name].append({
                        'filename': asset.name,
                        'url': asset.url,
                        'size': asset.size,
                        'upload_time': asset.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'version': version,
                    })

    def generate_index_html(self):
        # Generate main index
        package_list = self.packages.keys()
        main_index = HTML_TEMPLATE.format(
            package_name="Simple Package Index",
            package_links="\n".join([f'<a href="{x}/">{x}</a><br/>' for x in package_list])
        )

        with open(self.output_dir / "index.html", "w") as f:
            f.write(main_index)
 
        for package, assets in self.packages.items():

            package_dir = self.output_dir / package
            package_dir.mkdir(exist_ok=True)

            # Generate package-specific index.html
            file_links = []
            assets = sorted(assets, key=lambda x: x["filename"])
            for filename, items in itertools.groupby(assets, key=lambda x: x["filename"]):
                asset_info = next(items)
                url = asset_info['url']
                version = asset_info['version']

                # Download the file
                with open(package_dir / filename, 'wb') as f:
                    print (f"Downloading '{filename}' from '{url}'")
                    response = self.session.get(url, stream=True)
                    response.raise_for_status()
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                sha256_hash = calculate_sha256(package_dir / filename)

                # Check if this version is yanked
                yanked_attr = ""
                if self.is_version_yanked(package, version):
                    yanked_attr = ' data-yanked="true"'

                file_links.append(
                    f'<a href="{quote(filename)}#sha256={sha256_hash}"{yanked_attr}>{filename}</a><br/>'
                )

            package_index = HTML_TEMPLATE.format(
                package_name=f"Links for {package}",
                package_links="\n".join(file_links)
            )

            with open(package_dir / "index.html", "w") as f:
                f.write(package_index)

    def build(self):
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Collect and generate
        self.collect_packages()
        self.generate_index_html()


def main():
    # Get environment variables
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    print (repo)
    output_dir = os.environ.get("OUTPUT_DIR", "dist")
    
    if not all([token, repo]):
        print ("Missing required environment variables")
        sys.exit(1)

    builder = PackageIndexBuilder(token, repo, output_dir, yanked_versions)
    builder.build()

if __name__ == "__main__":
    main()
