# plugins/exif_metadata_extraction.py
import requests
from bs4 import BeautifulSoup
import re
from PIL import Image
from io import BytesIO
import exifread
from docx import Document
from openpyxl import load_workbook
from PyPDF2 import PdfReader
import hashlib
from plugins.base_plugin import BasePlugin


class ExifMetadataExtractionPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Exif Data and Metadata in Media Files"

    @property
    def description(self) -> str:
        return (
            "Extract Exif metadata from images, metadata from documents (Word, Excel, PDFs), and perform reverse image search."
        )

    @property
    def data_format(self) -> str:
        return "json"

    @property
    def required_api_keys(self) -> list:
        return []

    def run(self, target: str) -> dict:
        results = {}
        try:
            url = self.normalize_url(target)
            response = self.fetch_response(url)
            if not response:
                results["Error"] = "Failed to retrieve website response."
                return results

            # 1. Extract Media Files URLs
            media_files = self.extract_media_files(url, response.text)
            results["MediaFiles"] = media_files

            # 2. Extract Exif Metadata from Images
            exif_data = self.extract_exif_metadata(media_files)
            results["ExifMetadata"] = exif_data

            # 3. Extract Metadata from Documents
            document_metadata = self.extract_document_metadata(media_files)
            results["DocumentMetadata"] = document_metadata

            # 4. Perform Reverse Image Search (Image Hashing)
            reverse_image_search = self.perform_reverse_image_search(media_files)
            results["ReverseImageSearch"] = reverse_image_search

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith("http"):
            target = "http://" + target
        return target

    def fetch_response(self, url: str) -> requests.Response:
        try:
            headers = {
                "User-Agent": "DeepWebsiteAnalyzer/1.0"
            }
            response = requests.get(url, headers=headers, timeout=15)
            return response
        except requests.RequestException:
            return None

    def extract_media_files(self, base_url: str, html: str) -> dict:
        media_files = {
            "Images": [],
            "Documents": []
        }
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # Extract image sources
            for img in soup.find_all('img'):
                src = img.get('src')
                if src:
                    full_url = self.make_absolute_url(base_url, src)
                    media_files["Images"].append(full_url)
            # Extract document links
            doc_extensions = ['.pdf', '.docx', '.xlsx', '.doc', '.xls']
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(href.lower().endswith(ext) for ext in doc_extensions):
                    full_url = self.make_absolute_url(base_url, href)
                    media_files["Documents"].append(full_url)
        except Exception:
            pass
        return media_files

    def extract_exif_metadata(self, media_files: dict) -> dict:
        exif_data = {}
        try:
            for img_url in media_files.get("Images", []):
                try:
                    response = requests.get(img_url, timeout=10)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        exif = img._getexif()
                        if exif:
                            exif_info = {}
                            for tag, value in exif.items():
                                decoded = Image.ExifTags.TAGS.get(tag, tag)
                                exif_info[decoded] = value
                            exif_data[img_url] = exif_info
                        else:
                            exif_data[img_url] = "No Exif data found."
                except Exception:
                    exif_data[img_url] = "Failed to retrieve Exif data."
        except Exception as e:
            exif_data["Error"] = str(e)
        return exif_data

    def extract_document_metadata(self, media_files: dict) -> dict:
        document_metadata = {}
        try:
            for doc_url in media_files.get("Documents", []):
                try:
                    response = requests.get(doc_url, timeout=10)
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '').lower()
                        if 'application/pdf' in content_type:
                            reader = PdfReader(BytesIO(response.content))
                            info = reader.metadata
                            metadata = {key: str(value) for key, value in info.items()}
                            document_metadata[doc_url] = metadata
                        elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                            doc = Document(BytesIO(response.content))
                            core_properties = doc.core_properties
                            metadata = {
                                "title": core_properties.title,
                                "author": core_properties.author,
                                "last_modified_by": core_properties.last_modified_by,
                                "created": str(core_properties.created),
                                "modified": str(core_properties.modified)
                            }
                            document_metadata[doc_url] = metadata
                        elif 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
                            wb = load_workbook(filename=BytesIO(response.content), read_only=True)
                            props = wb.properties
                            metadata = {
                                "title": props.title,
                                "creator": props.creator,
                                "last_modified_by": props.last_modified_by,
                                "created": str(props.created),
                                "modified": str(props.modified)
                            }
                            document_metadata[doc_url] = metadata
                        else:
                            document_metadata[doc_url] = "Unsupported document type."
                except Exception:
                    document_metadata[doc_url] = "Failed to retrieve document metadata."
        except Exception as e:
            document_metadata["Error"] = str(e)
        return document_metadata

    def perform_reverse_image_search(self, media_files: dict) -> dict:
        reverse_search = {}
        try:
            for img_url in media_files.get("Images", []):
                try:
                    response = requests.get(img_url, timeout=10)
                    if response.status_code == 200:
                        img_content = response.content
                        img_hash = hashlib.md5(img_content).hexdigest()
                        reverse_search[img_url] = f"MD5 Hash: {img_hash}"
                        # Optionally, implement hash-based online searches
                    else:
                        reverse_search[img_url] = "Failed to retrieve image for hashing."
                except Exception:
                    reverse_search[img_url] = "Failed to perform reverse image search."
        except Exception as e:
            reverse_search["Error"] = str(e)
        return reverse_search

    def make_absolute_url(self, base: str, link: str) -> str:
        return requests.compat.urljoin(base, link)
