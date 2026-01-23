from pathlib import Path


class HtmlUtils:
    @staticmethod
    def load(filename: str) -> str:
        """Load an HTML file from the tests/scanner_adapter directory by filename.

        Returns the file content as a UTF-8 string.
        """
        test_dir = Path(__file__).parent
        file_path = test_dir / filename
        return file_path.read_text(encoding='utf-8')

