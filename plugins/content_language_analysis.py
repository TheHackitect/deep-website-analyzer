# plugins/content_language_analysis.py
import requests
from bs4 import BeautifulSoup
from langdetect import detect, DetectorFactory
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from plugins.base_plugin import BasePlugin
from collections import Counter
import string

# Ensure deterministic results in langdetect
DetectorFactory.seed = 0

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('vader_lexicon')
from nltk.sentiment import SentimentIntensityAnalyzer


class ContentLanguageAnalysisPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Content and Language Analysis"

    @property
    def description(self) -> str:
        return (
            "Perform keyword extraction, sentiment analysis, language detection, internationalization support, "
            "language tags, and localization settings."
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
            # 1. Fetch Content
            content = self.fetch_content(url)
            if not content:
                results["Error"] = "Failed to retrieve content."
                return results

            # 2. Language Detection
            language = self.detect_language(content)
            results["Language"] = language

            # 3. Sentiment Analysis
            sentiment = self.analyze_sentiment(content)
            results["Sentiment"] = sentiment

            # 4. Keyword Extraction
            keywords = self.extract_keywords(content)
            results["Keywords"] = keywords

            # 5. Language Tags and Localization Settings
            lang_tags = self.get_language_tags(url)
            results["LanguageTags"] = lang_tags

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith("http"):
            target = "http://" + target
        return target

    def fetch_content(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Remove scripts and styles
                for script_or_style in soup(['script', 'style']):
                    script_or_style.decompose()
                text = soup.get_text(separator=' ')
                return text
            else:
                return ""
        except requests.RequestException:
            return ""

    def detect_language(self, text: str) -> str:
        try:
            language = detect(text)
            return language
        except Exception as e:
            return f"Error detecting language: {str(e)}"

    def analyze_sentiment(self, text: str) -> dict:
        try:
            sia = SentimentIntensityAnalyzer()
            sentiment = sia.polarity_scores(text)
            return sentiment
        except Exception as e:
            return {"Error": str(e)}

    def extract_keywords(self, text: str) -> list:
        try:
            # Tokenize the text
            words = word_tokenize(text.lower())
            # Remove punctuation and stopwords
            stop_words = set(stopwords.words('english'))
            words = [
                word for word in words
                if word.isalpha() and word not in stop_words
            ]
            # Get the most common words as keywords
            word_counts = Counter(words)
            common_words = word_counts.most_common(10)
            keywords = [word for word, count in common_words]
            return keywords
        except Exception as e:
            return [f"Error extracting keywords: {str(e)}"]

    def get_language_tags(self, url: str) -> dict:
        lang_tags = {}
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                html_tag = soup.find('html')
                if html_tag and html_tag.has_attr('lang'):
                    lang_tags["html_lang"] = html_tag['lang']
                else:
                    lang_tags["html_lang"] = "Not specified."
            else:
                lang_tags["html_lang"] = "Failed to retrieve HTML."
        except requests.RequestException as e:
            lang_tags["html_lang"] = f"Error: {str(e)}"
        return lang_tags
